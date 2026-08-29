# agent-hive — A Contract-Driven Multi-Agent Orchestration Framework

**One-line positioning**: a single "chief" agent orchestrates role-specialist agents — it sets the architecture, dispatches contract-bound work packages, and reviews/integrates results. **Contracts are first-class citizens at runtime**, and architecture security validation plus cost budgeting are embedded as first-class primitives at the approval gates, emitted as standard artifacts (JSON Schema / SARIF / OTel JSONL).

This repository hosts two runtimes that share one contract (`skill/contracts.md`, rendered from the single source of truth `agent_hive/contract_spec.py`):

| Host | Location | Usage |
|---|---|---|
| **DSH skill** (in-session chief) | `skill/` | Copy to `~/.dsh/skills/agent-hive/`; triggers on "chief/orchestrate/agent swarm" topics |
| **LangGraph program** (standalone) | `agent_hive/` | `uv run python -m agent_hive run --goal "..."` |

## Four blank-dimension differentiators

> Market research (as of 2026-08): mainstream agent frameworks (OpenAI Agents SDK / Claude Agent SDK / ADK / LangGraph) all lack first-class cost-budget and model-circuit-breaker primitives. Our differentiation is the **combination** of the four dimensions below — every claim is falsifiable (auditable scope + rule version + evidence, see module READMEs and `benchmarks/`).

| # | Dimension | Selling point | Evidence |
|---|---|---|---|
| ① | **Contracts as first-class citizens + drift prevention** | Package contracts are machine-readable single sources of truth: Pydantic `PackageSpec` → public JSON Schema (`contracts/workpackage.schema.json`) → `contract-lint` CLI → `generate_contracts.py --check` drift gate in CI | `contracts/`, `scripts/contract_lint.py` |
| ② | **Contract-level HITL acceptance loop** | Failed reviews auto-return with feedback (≤3 rounds then circuit-break, with responsibility attribution); human approval happens only at two **contract-level gates** (architecture plan + batch table), not per tool call | `agent_hive/`, `docs/card-async-hitl.md` |
| ③ | **Architecture security validation embedded at the approval gate** | Before gate ① the `hive-security` deterministic rule engine runs (hallucinated references / dependency cycles / missing security controls / anti-patterns; 12-threat catalog mapped to CWE + OWASP LLM Top 10 2025); `fail` auto-recycles the architecture; SARIF/exit codes plug into CI | `hive_security/`, `benchmarks/security/` |
| ④ | **Cost budgeting + model resilience as first-class primitives** | Standalone `hive-cost`: `CostGate` budget checks / degradation chain / blocking + retry / circuit breaker / fallback chain, OTel-compatible JSONL export (consumable by Langfuse/LangSmith); missing from all mainstream agent SDKs | `hive_cost/`, `benchmarks/cost/` |

## 30-second demo

**Architecture security validation** (standalone package, one command):

```bash
pip install hive-security
hive-security scan --input arch.json --format sarif --output report.sarif
# exit codes: 0 = pass/pass_with_warnings; 2 = fail (CI-blocking); 3 = execution error
# arch.json shape: {"overview": "...", "modules": [{name, responsibility, interfaces,
#   owner_role, depends_on?}], "risks": ["..."]}
```

**Cost budgeting** (standalone package, instrument before/after calls):

```python
from hive_cost.budget import CostBudget
from hive_cost.gate import CostGate

gate = CostGate(budget=CostBudget(max_tokens=100_000, warn_ratio=0.8))
decision = gate.check_before_call("deepseek-chat", "coder")   # proceed / downgrade / block
gate.record_after_call("deepseek-chat", "coder", 1200, 300)   # cost estimated from price table
gate.to_otel_events()                                         # OTel-compatible events, JSONL export
```

## Benchmark (real numbers, reproducible)

> All figures are produced deterministically by `benchmarks/` (no `random`; two consecutive runs are byte-identical). See `benchmarks/README.md` for reproduction.

| Benchmark | Result | Reproduce |
|---|---|---|
| **Security** (129 samples = 14 hand-written + 115 template-generated, 10 threat families) | detection rate **1.0000** / false-positive rate **0.0000** / verdict accuracy **1.0000** (129/129 passing); avg latency 0.08 ms / p99 0.54 ms (machine-dependent) | `uv run python benchmarks/security/run.py` |
| **Cost** (100 tasks × 3–20 model calls each, three budget tiers) | completion 100.0% → 64.0% (70% budget) → 52.2% (50% budget); mean task cost $0.0040 → $0.0026 → $0.0019; downgrades 0 → 95 → 85; blocks 0 → 37 → 47; alerts 0 → 227 → 217 | `uv run python benchmarks/cost/run.py` |

## Scope / Out-of-scope statement

**In scope**: `hive-security` is a deterministic rule engine that consumes structured architecture JSON only (no markdown/source parsing) and runs four checks — hallucinated references, dependency cycles (3-color DFS), missing security controls (threat keyword hit without control words, 12-threat catalog), and architectural anti-patterns (empty risks / missing owner / module count out of range / execution interfaces without degradation design). SARIF output carries CWE / OWASP LLM Top 10 (2025) mappings. `hive-cost` covers budget checks, degradation chains, circuit breakers / retry / fallback, and OTel-compatible export.

**Out of scope**: no source-code parsing, no dependency/supply-chain scanning, no dynamic penetration testing; no LLM semantic-validation channel (`llm_enabled` is pass-through only); no "absolutely secure" claims — "pass" means only that no rule matched for the given input and rule version; costs are estimates (built-in static price table), not a billing API. Full statements: `hive_security/README.md`, `hive_cost/README.md`.

## Install / quick start

```bash
# Standalone components (consumable by any framework)
pip install hive-security hive-cost

# This repository (full framework + tests + benchmarks)
git clone <repo-url> && cd agent-hive
uv sync                        # installs deps incl. hive-security / hive-cost (editable)
uv run python -m agent_hive run --goal "Build a CLI todo manager (Python)"
```

## Features

- **Chief protocol**: survey agents → architecture → gate ① → contract-bound work packages → gate ② → dependency-layer dispatch → review → integration
- **Contract-first**: every package carries an interface contract, `expected_output`, `depends_on`, and tickable acceptance criteria
- **Evaluate-optimize loop**: failed reviews auto-resubmit with concrete gaps; per-package counter, circuit-break after ≤3 retries; `reassign_to` attributes defects within the active wave; cross-wave attribution warns and keeps passed packages frozen
- **Guardrails**: input guard (dangerous-goal interception), output guard (deliverable existence + path validation before LLM review), circuit-break guard
- **Dependency-aware fan-out**: same-layer `Send` branches run concurrently; downstream waits for dependencies; retries re-dispatch only the target package; break propagation blocks downstream
- **Integration guard**: passed packages merge into a unified `dist/`; same-path conflicts are rejected; static compile, `manifest.json`, staging atomic replace
- **Project board**: auditable artifact state machine (pending → in progress → awaiting review → passed / rework → broken / blocked)
- **Permission tiers T0/T1/T2**: full access (location hints + narrow probes) / workspace-only (engineering prompt pack first, then team survey) / zero-disclosure (advisor mode)
- **Dispatch eligibility review**: external agents are invoked only if "capability wins + time/cost efficient" both hold (no evidence → no dispatch)
- **Cost observability**: every run persists `cost.json` (model call counts and token usage)
- **Architecture security validation**: dual-channel check (rule engine + LLM semantics) before gate ①; `fail` auto-recycles; security report shown with the approval ticket; `--skip-arch-security` / `--allow-insecure-architecture` explicit switches audited
- **Resumable runs**: `--run-id` + `--thread-id` resume interrupted runs

## Verification (global gate)

```bash
uv run python scripts/verify.py          # pytest + compileall + contract drift + contract lint + golden
uv run pytest -q                         # currently: 409 passed
uv run python -m compileall -q agent_hive tests
uv run python scripts/generate_contracts.py --check
uv run python scripts/security_benchmark.py   # security benchmark (129 samples)
uv run python benchmarks/security/run.py      # reproducible benchmark report
uv run python benchmarks/cost/run.py          # cost benchmark (three tiers)
```

## Design provenance (inspirations)

- [MetaGPT](https://github.com/FoundationAgents/MetaGPT) (shared message pool / typed artifacts) → project board + structured reports + shared workspace
- [CrewAI](https://github.com/crewAIInc/crewAI) (manager evaluation/rework, expected_output, task dependencies) → evaluate-optimize loop + structured package fields
- [LangGraph](https://github.com/langchain-ai/langgraph) (supervisor, Send fan-out, interrupt) → graph orchestration + approval gates
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) (guardrails, max_turns) → guardrails + circuit breaking
- [Anthropic multi-agent patterns](https://claude.com/blog/common-workflow-patterns-for-ai-agents-and-when-to-use-them) (orchestrator-workers, evaluator-optimizer) → chief-specialists + review loop
- Claude Code subagents (handoff docs, file ownership, context economy) → restricted tools + handoff docs

## Security

LLMs hold file and command tools here — **command execution is disabled by default**; the full security model lives in [SECURITY.md](SECURITY.md). No token/secret ever appears in this repository: API keys live only in local `.env` (gitignored); PyPI publishing uses Trusted Publishing (OIDC) with no plaintext credentials in CI.

## License

[MIT](LICENSE) (`hive_security/` and `hive_cost/` each carry a LICENSE file, shipped inside their wheels)
