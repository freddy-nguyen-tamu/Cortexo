# Deterministic regression & progress reporting

The platform's build rules forbid reporting fabricated pass/fail. A field that
says "passed" must be backed by an executable command. The deterministic
regression harness extends that guarantee to the layer that produces the
"passed" verdict itself: it re-runs **fixed, committed good/bad fixtures**
through the exact same executable grader used for model evaluations and fails
the build whenever the grader's verdicts drift.

## What "deterministic" means here

A *regression* is defined as a mismatch between **expected** and **actual**
classification — not merely a failing test run. Concretely:

- expected `PASS`, actual `PASS` → match.
- expected `TEST_FAIL`, actual `TEST_FAIL` → match (the fixture is *supposed*
  to be broken; the grader correctly reports it broken).
- expected `TEST_FAIL`, actual `PASS` → regression (the grader stopped
  catching a bug).
- expected `TEST_FAIL`, actual `COMPILE_FAIL` → still a regression: the
  status **and** the pass/fail bit must both match, so a changed failure mode
  is surfaced instead of swallowed.
- a harness error (`HARNESS_ERROR`) is always a mismatch for that case.

The baseline therefore contains both known-goods and known-bads. A suite that
only passed known-goods would pass if the grader became a rubber stamp.

## Layout

```
benchmarks/baselines/deterministic-v1.json   committed baseline (11 cases)
benchmarks/baselines/fixtures/correct/       known-good candidates
benchmarks/baselines/fixtures/incorrect/     known-bad candidates
benchmarks/baselines/fixtures/invalid/       invalid/syntax-error candidates
scripts/run_regression.py                    CLI entrypoint
ml/src/cortexo_ml/evaluation/regression.py   harness, reports, public views
ml/tests/test_regression.py                  unit suite (no Docker needed)
artifacts/evaluations/regression/            generated reports (git-ignored)
```

The baseline suite (`deterministic-v1`) pins `requiredScore: 1.0`: every case
must match or the gate fails.

## Running

```bash
make regression                   # full mode: software checks + baseline cases
make regression-fast              # software checks only (no sandbox)
make regression-grader            # baseline cases only; enables the grader
make regression-show              # pretty-print the latest report
```

Direct invocation:

```bash
python scripts/run_regression.py --mode full
python scripts/run_regression.py --mode grader --no-history
python scripts/run_regression.py --mode software --json
```

Modes:

- `full` — software checks **and** deterministic baseline cases.
- `grader` — deterministic baseline cases only.
- `software` — repository health checks only, no sandbox, no Docker.

The report is always produced even when a check fails; the exit code (0/1)
reflects the requested gate. Because `grader` mode intentionally omits the
software section, a stale compiler never fails a grader-only run, and
`software` mode never fails because the sandbox/docker image is absent.

## Software checks

`python-compile`, `python-tests`, `sandbox-build` (docker image build),
`vue-typecheck`, `vue-build`, `spring-tests`, and `gold-patch-assignment`
(scans the task files for the forbidden literal `patch = task.get("gold_patch")`).

## Reports

Timestamped reports plus `latest.json` are written to the git-ignored
`artifacts/evaluations/regression/`:

```
schemaVersion: 1
suiteVersion, generatedAt
git:           commit, shortCommit, branch, dirty
environment:   python, java, maven, node, npm, docker, sandboxImage
baselineSha256
requested:     software / deterministic flags
summary:       software, deterministic (incl. byCategory), overall,
               requiredDeterministicScore, passedGate
checks:        software-check records
cases:         per-case expected/actual status, passed, matched, duration,
               candidate_sha256, changed_files, changed_lines, message
delta:         previous/current overall score, scoreDelta, changedCases
```

When the previous report exists and its `suiteVersion` matches, the new report
carries a `delta` section (computed **before** `latest.json` is overwritten).

### Public (browser-safe) projection

The API surface serves `public_regression_report` / `public_regression_summary`
projections, which strip stdout/stderr, command vectors, raw candidate source,
hidden-test source, gold patches, environment details and expected behaviors.
The browser sees only classification metadata.

## API

FastAPI gateway (read-only — there is deliberately **no** job trigger):

- `GET /v1/regression/latest` — sanitized latest report, or 404.
- `GET /v1/regression/history?limit=N` — N clamped to 1..100.

Spring passthrough:

- `GET /api/benchmarks/regression/latest`
- `GET /api/benchmarks/regression/history?limit=N`

The Spring gateway client degrades to `{"available": false}` (HTTP 200) when
the ML gateway is unreachable instead of throwing; the Vue panel renders the
empty state.

## UI

The Benchmarks page renders `RegressionProgressPanel` above the executable
grader panel: an Overall PASS/FAIL pill, suite/commit/score/baseline cards,
the score delta and changed cases since the previous run, the per-case
expected-vs-actual table, the software-check table, and a history table with
the current run highlighted. PASS and FAIL are always explicit text.

## Training-data exclusion

`ml/src/cortexo_ml/data/collect.py` skips any path under
`benchmarks/baselines/` (tag `evaluation-baseline`) and
`benchmarks/hidden_tests/` (tag `hidden-test`) *before* license scoring.
`datasets/manifests/exclusions.json` sets `neverInclude.deterministicBaselines
= true` and adds `benchmarks/baselines` to `paths`. Baseline answers can never
enter a training corpus.

## CI

`.github/workflows/regression.yml` runs `python scripts/run_regression.py
--mode full --no-history` on push/PR (no generated report is committed).
The harness falls back to `sys.executable` when `ml/.venv` is absent.

## Adding cases

1. Drop a fixture under `benchmarks/baselines/fixtures/{correct,incorrect,invalid}/`.
2. Reference it from `deterministic-v1.json` with a unique `id`, the canonical
   `taskId`, `category`, `expectedStatus`, `expectedPassed` and `candidate`.
3. Run `make regression-grader` and confirm the fixture matches as intended.
4. Baseline hash changes intentionally; record the new expectation in the
   suite changelog.