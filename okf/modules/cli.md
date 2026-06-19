---
type: Module
title: CLI
description: The `milcah` command-line interface — ingest an input into a segmented framework, and extract typed reasoning units from it using either the deterministic baseline or the LLM-via-Hoglah extractor.
resource: https://github.com/gellsmore-svg/Milcah/blob/main/src/milcah/cli.py
tags: [milcah, cli]
timestamp: 2026-06-19T00:00:00Z
---

# CLI (`cli.py`)

The `milcah` command. With no subcommand it prints the project's purpose; the two
built commands take a file path or `-` for stdin and `--json`:

- **`milcah ingest`** — normalise an input into a segmented
  [`Framework`](models.md) (FR1); `--source-type` / `--title` overrides.
- **`milcah extract`** — [extract](extraction.md) typed
  [reasoning units](../concepts/reasoning-units.md) (FR1+FR2). `--extractor`
  selects `rule` (deterministic baseline) or `hoglah`
  ([LLM via Hoglah](hoglah-extractor.md)); `--model`, `--transport`
  (`store|kafka|rabbitmq|redis`), `--hoglah-db`, and `--timeout` configure the
  Hoglah path.

```bash
milcah extract framework.md
milcah extract framework.md --extractor hoglah --model gemma4:latest
```
