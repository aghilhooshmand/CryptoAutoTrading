# CryptoAutoTrading Development Workflow

## Purpose

This document defines the standard development lifecycle for
CryptoAutoTrading.

It complements:

- `.specify/memory/constitution.md` — project-wide rules and architectural
  constraints.
- `core/roadmap.md` — feature sequence, dependencies, and status.
- `specs/NNN-feature-name/` — detailed requirements and design for each feature.

The objective is to keep development specification-driven, testable,
traceable, incremental, and safe as the project evolves from simulation and
backtesting toward Torque, Grammatical Evolution, and eventually controlled
real-money trading.

---

# 1. Sources of Truth

Project decisions are divided between three levels.

## 1.1 Constitution

Location:

```text
.specify/memory/constitution.md
```

The constitution defines durable project-wide rules.

Examples:

- capital protection;
- single authoritative trading pipeline;
- Controller and Risk authority;
- execution abstraction;
- simulation before real money;
- strategy advisory-only behavior;
- Torque/GE architectural boundaries;
- testing requirements;
- roadmap synchronization;
- real-money safety.

A feature specification MUST comply with the constitution.

If a feature conflicts with a constitutional MUST, the conflict must be
resolved before clean implementation approval.

---

## 1.2 Roadmap

Location:

```text
core/roadmap.md
```

The roadmap defines:

- planned features;
- feature ordering;
- major dependencies;
- feature status;
- long-term architectural direction.

The roadmap MUST NOT replace detailed feature specifications.

---

## 1.3 Feature Specification

Location:

```text
specs/NNN-feature-name/
```

The feature specification defines the actual behavior of a feature.

Typical files:

```text
spec.md
plan.md
research.md
data-model.md
contracts/
quickstart.md
tasks.md
```

Later explicit clarifications override older conflicting wording and must be
reflected in the relevant specification documents.

---

# 2. Feature Status Lifecycle

Every roadmap feature uses one of these states:

```text
PLANNED
IN PROGRESS
BLOCKED
DEFERRED
DONE
```

Normal lifecycle:

```text
PLANNED
   ↓
SPECIFICATION
   ↓
IN PROGRESS
   ↓
IMPLEMENTATION
   ↓
VALIDATION
   ↓
DONE
```

`DONE` means more than "the code was written."

A feature may be marked DONE only when:

1. required implementation is complete;
2. required automated tests pass;
3. specification analysis/convergence has no unresolved blocking issue;
4. quickstart or required smoke tests pass;
5. documentation reflects implemented behavior;
6. roadmap impact has been reviewed.

---

# 3. Before Starting a Feature

Before creating a specification:

1. Open `core/roadmap.md`.
2. Identify the next feature.
3. Review its purpose and dependencies.
4. Confirm prerequisite features are sufficiently complete.
5. Review `.specify/memory/constitution.md`.
6. Check whether the proposed feature changes existing architectural
   assumptions.

Do not begin implementation directly from a roadmap description.

The roadmap defines direction, not sufficient implementation requirements.

---

# 4. Standard Spec Kit Workflow

The normal feature workflow is:

```text
Roadmap
   ↓
Specify
   ↓
Clarify
   ↓
Plan
   ↓
Tasks
   ↓
Analyze
   ↓
Remediate
   ↓
Implement
   ↓
Test
   ↓
Quickstart / Smoke
   ↓
Converge
   ↓
Documentation Review
   ↓
Roadmap Update
   ↓
Git Commit
```

Each stage has a distinct purpose.

---

# 5. Step 1 — Specify

Create the feature specification using the project's Spec Kit workflow.

Typical command:

```text
/speckit.specify
```

The specification should focus primarily on WHAT and WHY.

It should define:

- user goals;
- user stories;
- functional requirements;
- success criteria;
- edge cases;
- assumptions;
- scope;
- explicit non-goals.

For trading features, explicitly identify where the feature sits in:

```text
Market Data
    ↓
Strategy / Torque
    ↓
Controller
    ↓
Risk
    ↓
Execution
    ↓
Accounting / Portfolio
    ↓
Journal / Reporting
```

A feature MUST NOT silently introduce another trading path.

---

# 6. Step 2 — Clarify

Run clarification before architecture is locked.

Typical command:

```text
/speckit.clarify
```

Clarification should resolve decisions that materially change:

- API contracts;
- persistence;
- algorithms;
- risk behavior;
- execution semantics;
- history requirements;
- UI behavior;
- compatibility;
- tests.

Examples from previous features include:

- RSI crossover vs level behavior;
- Bollinger recovery semantics;
- warm-up requirements;
- strategy aliases;
- comparison leg limits;
- synchronous vs asynchronous comparison;
- retention limits.

Prefer explicit decisions over leaving behavior to implementation.

Once accepted, clarification decisions should be treated as locked unless new
evidence requires revisiting them.

---

# 7. Step 3 — Plan

Generate the implementation plan.

Typical command:

```text
/speckit.plan
```

The plan should determine HOW the feature fits into the existing architecture.

Review at least:

- existing modules to reuse;
- new modules;
- database changes;
- API changes;
- frontend changes;
- tests;
- compatibility;
- performance constraints;
- constitution compliance.

For trading features, explicitly verify:

```text
Strategy / Torque
        ↓
Controller
        ↓
Risk
        ↓
Execution Adapter
        ↓
Accounting / Portfolio
```

No plan should create strategy-specific execution infrastructure when shared
infrastructure already exists.

---

# 8. Step 4 — Review Design Artifacts

Before generating tasks, inspect:

```text
spec.md
plan.md
research.md
data-model.md
contracts/
quickstart.md
```

Check for contradictions.

Important examples:

- spec vs research;
- research vs data model;
- contract vs implementation plan;
- warm-up vs insufficient-history rules;
- UI types vs API types;
- persistence vs compatibility behavior.

Resolve material contradictions before implementation.

---

# 9. Step 5 — Generate Tasks

Typical command:

```text
/speckit.tasks
```

Tasks should be:

- concrete;
- independently understandable;
- mapped to requirements/user stories;
- explicit about file paths;
- ordered by dependency;
- testable.

Trading-critical tests should normally be tasks, not implied implementation
details.

Prefer:

```text
Write failing fill-timing test
→ implement fill behavior
→ run test
```

over:

```text
Implement historical execution correctly
```

---

# 10. Step 6 — Analyze Before Implementation

Run specification analysis after tasks exist.

Typical command:

```text
/speckit.analyze
```

Analysis is an implementation gate, not merely informational output.

Review findings in this order:

```text
CRITICAL
HIGH
MEDIUM
LOW
```

---

# 11. Analysis Decision Rules

## CRITICAL

Must normally be resolved before implementation.

Examples:

- constitution MUST conflict;
- unsafe real-money behavior;
- contradictory execution authority;
- impossible requirement;
- missing trading-critical safety rule.

Do not ignore CRITICAL findings simply because implementation is possible.

---

## HIGH

Resolve before implementation whenever practical.

Examples:

- missing API proxy that makes UI unusable;
- unsupported parameter type;
- missing validation path;
- contradictory signal semantics;
- missing critical test coverage.

---

## MEDIUM

Evaluate individually.

Resolve when the ambiguity can materially affect behavior or future
compatibility.

---

## LOW

May be accepted/documented if it does not affect correctness or safety.

Do not churn working code merely to eliminate harmless duplication.

---

# 12. Remediation After Analysis

If analysis identifies meaningful issues:

1. modify `spec.md`, `plan.md`, `research.md`, contracts, or `tasks.md` as
   appropriate;
2. ensure all artifacts agree;
3. rerun analysis when changes are substantial;
4. proceed only when no unresolved blocking issue remains.

Do not patch the implementation to compensate for contradictory specifications
without correcting the specification.

---

# 13. Step 7 — Mark Feature IN PROGRESS

When implementation begins, update:

```text
core/roadmap.md
```

Example:

```text
007 Strategy Comparison | PLANNED
```

becomes:

```text
007 Strategy Comparison | IN PROGRESS
```

This update should occur as part of the implementation workflow.

---

# 14. Step 8 — Implement

Typical command:

```text
/speckit.implement
```

Implementation should follow `tasks.md`.

Do not opportunistically add unrelated features.

If implementation exposes a specification problem:

```text
STOP
→ inspect specification
→ clarify/change design
→ update tasks if necessary
→ continue
```

Do not silently redefine specified behavior in code.

---

# 15. Reuse Rule During Implementation

Before introducing new trading-domain logic, search for an existing
authoritative implementation.

Future features should reuse, where appropriate:

```text
Market Data
Strategy Registry
Controller
Risk
Portfolio
Capital Allocation
Execution
Accounting
Backtest
Decision Journal
Metrics
```

Torque and GE are especially subject to this rule.

Torque MUST NOT become a second trading engine.

GE MUST NOT become a third trading engine.

---

# 16. Tests During Implementation

Tests should run incrementally.

Do not wait until the end of a large feature to run the full suite.

Recommended sequence:

```text
new unit tests
↓
affected contract tests
↓
affected integration tests
↓
frontend tests
↓
existing regression tests
↓
full suite
```

Trading-critical failures must be investigated rather than hidden by weakening
tests.

---

# 17. Trading-Critical Test Expectations

Where applicable, test:

- strategy signals;
- warm-up;
- parameter validation;
- insufficient history;
- duplicate candle handling;
- Controller decisions;
- Risk rejection;
- position sizing;
- capital nesting;
- fill timing;
- fees;
- slippage;
- realized P&L;
- unrealized P&L;
- liquidation value;
- max drawdown;
- forced close;
- max trades;
- profit/loss boundaries;
- persistence;
- retention;
- determinism;
- restart behavior;
- API contracts;
- simulation/backtest isolation;
- execution adapter isolation.

For real-money features, additional tests are mandatory for exchange and
failure behavior.

---

# 18. Behavioral Continuity

When refactoring shared infrastructure, existing regression tests should remain
unchanged unless the new feature intentionally changes the behavior.

Example:

Feature 006 added RSI, MACD, Bollinger Bands, and Breakout.

Dual EMA continuity remained a regression gate.

Future execution abstraction should similarly preserve Simulation and Backtest
semantics unless explicitly changed by specification.

---

# 19. Quickstart Validation

After automated tests pass, execute the relevant:

```text
specs/NNN-feature-name/quickstart.md
```

Quickstart is an operator-level validation of the implemented feature.

It should test important real workflows rather than repeat unit tests.

Examples:

```text
create
run
inspect
restart
delete
reject invalid configuration
verify history
verify UI
```

---

# 20. Convergence

After implementation and testing, run the project's convergence workflow.

Typical command:

```text
/speckit.converge
```

The objective is to verify that:

```text
Specification
     ↕
Plan
     ↕
Tasks
     ↕
Implementation
     ↕
Tests
```

describe the same system.

A feature should not be marked DONE while meaningful convergence gaps remain.

---

# 21. Documentation Review

Before completion, inspect:

```text
README.md
core/roadmap.md
feature quickstart
API contracts
cross-feature contracts
configuration documentation
```

Update only documentation affected by the feature.

Avoid copying detailed implementation requirements into the roadmap.

---

# 22. Roadmap Completion Update

When all completion conditions are satisfied:

```text
IN PROGRESS → DONE
```

Example:

```text
| 007 | Strategy Comparison | DONE |
```

Then review later roadmap features.

Ask:

- Did this feature eliminate a planned feature?
- Did it create a prerequisite?
- Did terminology change?
- Did architecture change?
- Should future feature scope change?

Only update downstream entries when there is an actual reason.

---

# 23. Git Completion

After successful completion, prepare a meaningful commit.

Example:

```text
feat(007): implement strategy comparison
```

or:

```text
feat(strategy-comparison): add fair multi-strategy backtest comparison
```

The commit should reference the implemented feature where practical.

Tools may propose commits.

They MUST NOT automatically commit unless explicitly instructed.

---

# 24. Hotfix Workflow

Not every change requires a new numbered feature.

Small corrections may use a shorter workflow when they:

- fix a bug;
- correct documentation;
- repair a test;
- make no material architectural change;
- introduce no new product behavior.

Minimum hotfix process:

```text
identify bug
↓
write/reproduce failing test where appropriate
↓
fix
↓
affected regression tests
↓
document if externally visible
↓
commit
```

If a "bug fix" materially changes trading semantics, it is not merely a
hotfix. Update the relevant specification or create a new feature.

---

# 25. Architecture Change Workflow

Changes to fundamental concepts require stronger review.

Examples:

- trading pipeline;
- Controller authority;
- Risk authority;
- accounting semantics;
- execution model;
- portfolio authority;
- Torque language model;
- GE fitness architecture;
- real-money activation.

For these:

```text
review constitution
↓
review roadmap
↓
specify
↓
clarify
↓
plan
↓
analyze
↓
implement
```

Do not implement architectural changes first and document them afterward.

---

# 26. Settings Rule

Settings represent defaults for future work.

Example:

```text
Default starting capital = €500
Default fee = 0.001
Default slippage = 0.0005
```

Creating a run materializes those values into that run.

Later changing settings MUST NOT change historical runs.

Conceptually:

```text
Settings
   ↓ copy at creation
Run Configuration
   ↓
Persisted Historical Truth
```

This rule becomes particularly important for Features 008, 018, and 019.

---

# 27. Real-Money Development Gate

No feature may enable autonomous real-money trading merely because the
underlying strategy performed well in backtesting.

The expected progression is:

```text
Historical Backtest
       ↓
Simulation
       ↓
Long-running Paper Trading
       ↓
Private Exchange Integration
       ↓
Confirmed Real Execution
       ↓
Extensive Validation
       ↓
Autonomous Real Execution
```

Feature 023 is the explicit autonomous-real-money boundary.

---

# 28. Torque Development Rule

Torque programs may describe combinations such as:

```text
strategy
strategy parameters
time windows
sequence
capital allocation
signal composition
```

But execution remains:

```text
Torque
  ↓
Trading Intent
  ↓
Controller
  ↓
Risk
  ↓
Execution
  ↓
Accounting
```

Torque program evaluation SHOULD reuse the existing Backtest infrastructure
rather than create an independent historical trading implementation.

---

# 29. GE Development Rule

GE generates/searches Torque programs.

Conceptually:

```text
Genotype
   ↓ grammar mapping
Torque Phenotype
   ↓
Torque Evaluation
   ↓
Existing Backtest Infrastructure
   ↓
Metrics
   ↓
Fitness
```

Initial fitness may be:

```text
Fitness =
    Torque Program Net Profit
    - Buy & Hold Net Profit
```

Future features may extend this.

Every experiment must remain reproducible.

---

# 30. Train / Validation / Test Rule

Once optimization begins, historical data roles must be explicit.

```text
TRAIN
  GE searches

VALIDATION
  compare/select/tune according to experiment design

TEST
  final unseen evaluation
```

Test data MUST NOT influence evolutionary selection.

---

# 31. Feature Completion Checklist

Before marking any material feature DONE:

```text
[ ] Specification reflects final intended behavior
[ ] Clarifications incorporated
[ ] Plan matches specification
[ ] Tasks cover buildable requirements
[ ] Analysis has no unresolved blocker
[ ] Implementation complete
[ ] New unit tests pass
[ ] Contract tests pass
[ ] Integration tests pass
[ ] Relevant frontend tests pass
[ ] Existing regression tests pass
[ ] Trading-critical tests pass
[ ] Quickstart/smoke passes
[ ] Convergence passes
[ ] Documentation updated
[ ] Roadmap reviewed
[ ] Feature marked DONE
[ ] Commit proposed/prepared
```

Not every feature needs every test category, but every applicable category must
be considered.

---

# 32. Starting the Next Feature

Only after the previous feature's state is understood should the next roadmap
feature begin.

Normal sequence:

```text
Finish current feature
        ↓
Roadmap review
        ↓
Select next PLANNED feature
        ↓
Review dependencies
        ↓
Specify
```

For the current roadmap, after Strategy Comparison the next planned feature is:

```text
008 Trading & Experiment Defaults
```

unless roadmap priorities are intentionally changed.

---

# 33. Workflow Summary

The standard CryptoAutoTrading feature cycle is:

```text
1.  Check constitution
2.  Check roadmap
3.  /speckit.specify
4.  /speckit.clarify
5.  /speckit.plan
6.  Review design artifacts
7.  /speckit.tasks
8.  /speckit.analyze
9.  Fix important findings
10. Mark IN PROGRESS
11. /speckit.implement
12. Run incremental tests
13. Run full relevant tests
14. Run quickstart
15. /speckit.converge
16. Review documentation
17. Update roadmap → DONE
18. Prepare commit
19. Start next roadmap feature
```

This workflow is the default.

Deviation is acceptable for trivial fixes, but trading-critical or
architectural changes require the full process.