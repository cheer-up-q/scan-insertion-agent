# Scan Insertion Agent

LLM-based autonomous Scan Insertion agent for the EDA Elite Challenge 2026
(广立微 Scan Insertion track).

## What is implemented

- **A / DFT Flow** — Action IR 0.2.0 catalog, TaskRequirement → Action plan,
  Dofile renderer, DRC rule catalog, limitations parsing, Dofile patching.
- **B / Agent** — deterministic Task Parser, DeepSeek/Bailian LLM client,
  local manual RAG, state machine, budgets, log/DRC/scan-chain/wrapper
  diagnosis, deterministic repair, full orchestration loop.
- **C / Runtime** — case loader, run directory manager, tool runner,
  `ToolRunResult` collection, decision log, diffs, Yosys EQY interface,
  Docker entry point.

## Quick start (mock mode, no DFTEXP required)

```bash
pip install -r requirements-dev.txt

python -m src.cli \
  -input examples/public_case_demo \
  -output /tmp/out_case \
  --mock-tool --mock-llm
```

A runnable demo case can be created from `examples/task_specs/`; the test
suite builds its own cases.

## Tests

```bash
pytest
```

The suite covers:

- Task Parser acceptance fixtures and the six static-review edge cases;
- Action catalog/planner/renderer;
- Runtime, decision-log validation and diffs;
- Diagnosis and repair;
- End-to-end Task 1 and Task 2 mock runs, including chain-count,
  invalid-parameter, DRC and wrapper-scope repair.

## Official mode

The official DFTEXP command syntax and manual are not present in this
repository. Before a real submission:

1. fill `configs/dft_tool_templates.yaml` with verified command templates;
2. set `dft.dofile_mode: strict`;
3. set `tool.mode: real` and fill `tool.command`;
4. set `lec.mode: real` and ensure `eqy` is installed;
5. place the official manual under `manual/`;
6. set `DASHSCOPE_API_KEY` in the evaluation environment.

See `docs/competition_compliance.md` for the exact status of every official
requirement and the remaining gaps.

## Layout

```text
src/task_parser/     B: natural-language task parser
src/dft_flow/        A: Action IR, planner, Dofile renderer, DRC rules
src/agent/           B: LLM, RAG, diagnosis, repair, orchestration
src/case/            C: case loader
src/runtime/         C: run directories and final publication
src/tool_runner/     C: official tool wrapper + deterministic mock tool
src/audit/           C: decision log, diffs
src/lec/             C: Yosys EQY interface
configs/             runtime configuration
schemas/             Action IR schema
docs/                architecture and compliance documents
manual/              place the official DFTEXP manual here
```

## Honesty note

Mock mode is explicitly separate from real mode. The Agent never fabricates
tool logs, reports or deliverables. If a verified command template, the
official tool, or a required LEC is missing, the run is marked blocked or
failed rather than reported as successful.
