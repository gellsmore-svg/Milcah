"""LLM-backed reasoning extraction, executed through Hoglah (FR2 + FR4/FR5).

The deterministic `RuleBasedExtractor` is the transparent floor; this is the
quality path. It reuses the same seam (`build_extraction_prompt` /
`parse_extraction_response`) but routes the model call through **Hoglah** — the
family's execution layer — so extraction runs durably and at controlled
concurrency, against Ollama, via a separate `hoglah run --real` (or
`*-bridge`) daemon.

Two submission transports, both validated end-to-end:
- **store** (default) — submit to Hoglah's shared SQLite queue and block on
  `client.wait` (the daemon executes and writes the terminal result).
- **kafka | rabbitmq | redis** — publish a job-request and await the result over
  the broker via Hoglah's `MessagingSubmitter`.

The model call sits behind an injectable `submit(prompt, model) -> output`
callable, so `HoglahExtractor` is unit-testable without a daemon or broker.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from milcah.extraction import build_extraction_prompt, parse_extraction_response
from milcah.models import Framework, ReasoningUnit

# A reasoning-capable local model available via Ollama; override per deployment.
DEFAULT_MODEL = "gemma4:latest"

SubmitFn = Callable[[str, str], str]


class HoglahExtractionError(RuntimeError):
    """A Hoglah-executed extraction job failed or returned no usable output."""


@dataclass
class HoglahExtractorConfig:
    model: str = DEFAULT_MODEL
    timeout: float = 180.0
    transport: str = "store"  # store | kafka | rabbitmq | redis
    # store transport
    db_path: str = "data/hoglah/jobs.sqlite3"
    output_dir: str = "data/hoglah/outbox"
    # messaging transports
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_input_topic: str = "hoglah-jobs"
    kafka_results_topic: str = "hoglah-results"
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_input_queue: str = "hoglah-jobs"
    redis_url: str = "redis://localhost:6379/0"
    redis_input_stream: str = "hoglah-jobs"
    redis_results_stream: str = "hoglah-results"


class HoglahExtractor:
    """Reasoning extraction whose model call runs through Hoglah → Ollama."""

    def __init__(
        self,
        config: HoglahExtractorConfig | None = None,
        *,
        submit: SubmitFn | None = None,
        per_segment: bool = False,
    ) -> None:
        self.config = config or HoglahExtractorConfig()
        self.per_segment = per_segment
        self._submit = submit  # injected (prompt, model) -> output, for tests / single
        self._submitter: _Submitter | None = None  # built lazily from config

    def _get_submitter(self) -> _Submitter:
        if self._submitter is None:
            self._submitter = make_hoglah_submitter(self.config)
        return self._submitter

    def _run_one(self, prompt: str) -> str:
        if self._submit is not None:
            return self._submit(prompt, self.config.model)
        return self._get_submitter().run(prompt, self.config.model)

    def _run_batch(self, prompts: list[str]) -> list[str]:
        if self._submit is not None:
            return [self._submit(p, self.config.model) for p in prompts]
        return self._get_submitter().run_batch(prompts, self.config.model)

    def extract(self, framework: Framework) -> list[ReasoningUnit]:
        if self.per_segment and framework.segments:
            return self._extract_per_segment(framework)
        output = self._run_one(build_extraction_prompt(framework))
        return parse_extraction_response(output, framework)

    def _extract_per_segment(self, framework: Framework) -> list[ReasoningUnit]:
        """One extraction job per segment, merged with segment provenance. Keeps
        long frameworks within the model's context window, lets one bad segment
        fail without losing the rest, and (via the store transport's batch submit)
        runs the jobs at the daemon's configured concurrency."""
        prompts = [build_extraction_prompt(framework, text=seg.text) for seg in framework.segments]
        outputs = self._run_batch(prompts)
        units: list[ReasoningUnit] = []
        for seg, output in zip(framework.segments, outputs):
            units.extend(parse_extraction_response(output, framework, segment_index=seg.index))
        return units

    def close(self) -> None:
        if self._submitter is not None:
            self._submitter.close()
            self._submitter = None


class _Submitter:
    """A configured Hoglah submission backend with single + batch execution."""

    def run(self, prompt: str, model: str) -> str:
        raise NotImplementedError

    def run_batch(self, prompts: list[str], model: str) -> list[str]:
        raise NotImplementedError

    def close(self) -> None:
        pass


class _StoreSubmitter(_Submitter):
    """SQLite-store transport: submit all jobs, then await them — the separate
    `hoglah run` daemon executes them at its concurrency (1 by default; parallel
    with concurrency>1 or extra workers)."""

    def __init__(self, config: HoglahExtractorConfig) -> None:
        from hoglah import Hoglah, JobStatus

        self._JobStatus = JobStatus
        self._timeout = config.timeout
        self._client = Hoglah(
            config={"db_path": config.db_path, "output_dir": config.output_dir},
            start_worker=False,
        )

    def run(self, prompt: str, model: str) -> str:
        return self.run_batch([prompt], model)[0]

    def run_batch(self, prompts: list[str], model: str) -> list[str]:
        job_ids = [
            self._client.submit(
                prompt=p, model=model, timeout_seconds=int(self._timeout),
                tags=["milcah", "extraction"], metadata={"source": "milcah"},
            )
            for p in prompts
        ]
        outputs: list[str] = []
        for job_id in job_ids:
            result = self._client.wait(job_id, timeout=self._timeout)
            if result.status != self._JobStatus.COMPLETED:
                raise HoglahExtractionError(
                    result.error or f"Hoglah job {job_id} ended with status {result.status}."
                )
            outputs.append(result.output or "")
        return outputs

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()


class _MessagingSubmitter(_Submitter):
    """Broker transport (kafka/rabbitmq/redis) via Hoglah's MessagingSubmitter.
    That submitter is one-in-flight, so a batch runs sequentially."""

    def __init__(self, config: HoglahExtractorConfig) -> None:
        from hoglah.messaging_submitter import MessagingSubmitter, make_submitter_transport

        self._timeout = config.timeout
        self._submitter = MessagingSubmitter(
            make_submitter_transport(
                config.transport,
                kafka_bootstrap_servers=config.kafka_bootstrap_servers,
                kafka_input_topic=config.kafka_input_topic,
                kafka_results_topic=config.kafka_results_topic,
                rabbitmq_url=config.rabbitmq_url,
                rabbitmq_input_queue=config.rabbitmq_input_queue,
                redis_url=config.redis_url,
                redis_input_stream=config.redis_input_stream,
                redis_results_stream=config.redis_results_stream,
            )
        )

    def run(self, prompt: str, model: str) -> str:
        result = self._submitter.submit(
            kind="generate", prompt=prompt, model=model, timeout=self._timeout,
            tags=["milcah", "extraction"], metadata={"source": "milcah"},
        )
        if result.get("status") != "completed":
            raise HoglahExtractionError(
                result.get("error") or f"Hoglah job ended with status {result.get('status')}."
            )
        return result.get("output") or ""

    def run_batch(self, prompts: list[str], model: str) -> list[str]:
        return [self.run(p, model) for p in prompts]

    def close(self) -> None:
        self._submitter.close()


def make_hoglah_submitter(config: HoglahExtractorConfig) -> _Submitter:
    """Build the Hoglah submission backend for the configured transport. Imports
    of Hoglah / broker libraries are deferred here so the module imports without
    the optional `hoglah` dependency installed."""
    if config.transport == "store":
        return _StoreSubmitter(config)
    return _MessagingSubmitter(config)
