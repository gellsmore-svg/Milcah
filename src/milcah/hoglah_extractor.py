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
        self, config: HoglahExtractorConfig | None = None, *, submit: SubmitFn | None = None
    ) -> None:
        self.config = config or HoglahExtractorConfig()
        self._submit = submit  # injectable; built lazily from config when None

    def extract(self, framework: Framework) -> list[ReasoningUnit]:
        submit = self._submit or make_hoglah_submit(self.config)
        prompt = build_extraction_prompt(framework)
        output = submit(prompt, self.config.model)
        return parse_extraction_response(output, framework)


def make_hoglah_submit(config: HoglahExtractorConfig) -> SubmitFn:
    """Build the real Hoglah submission callable for the configured transport.

    Imports of Hoglah / broker libraries are deferred to here so the rest of the
    module imports without the optional `hoglah` dependency installed.
    """
    if config.transport == "store":
        return _store_submit(config)
    return _messaging_submit(config)


def _store_submit(config: HoglahExtractorConfig) -> SubmitFn:
    from hoglah import Hoglah, JobStatus

    client = Hoglah(
        config={"db_path": config.db_path, "output_dir": config.output_dir},
        start_worker=False,  # a separate `hoglah run --real` daemon executes jobs
    )

    def submit(prompt: str, model: str) -> str:
        job_id = client.submit(
            prompt=prompt,
            model=model,
            timeout_seconds=int(config.timeout),
            tags=["milcah", "extraction"],
            metadata={"source": "milcah"},
        )
        result = client.wait(job_id, timeout=config.timeout)
        if result.status != JobStatus.COMPLETED:
            raise HoglahExtractionError(
                result.error or f"Hoglah job {job_id} ended with status {result.status}."
            )
        return result.output or ""

    return submit


def _messaging_submit(config: HoglahExtractorConfig) -> SubmitFn:
    from hoglah.messaging_submitter import MessagingSubmitter, make_submitter_transport

    submitter = MessagingSubmitter(
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

    def submit(prompt: str, model: str) -> str:
        result = submitter.submit(
            kind="generate",
            prompt=prompt,
            model=model,
            timeout=config.timeout,
            tags=["milcah", "extraction"],
            metadata={"source": "milcah"},
        )
        if result.get("status") != "completed":
            raise HoglahExtractionError(
                result.get("error") or f"Hoglah job ended with status {result.get('status')}."
            )
        return result.get("output") or ""

    return submit
