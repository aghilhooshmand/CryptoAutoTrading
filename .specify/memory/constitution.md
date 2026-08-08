<!--
Sync Impact Report
- Version change: (template/unset) → 1.0.0
- Modified principles: N/A (initial ratification from template placeholders)
- Added sections:
  - Core Principles (I–XV): capital protection, modes, pipeline, risk authority,
    session bounds, net P&L, journals, fail-safe, emergency stop, simplicity,
    strategies, evidence vs guarantees, no guaranteed-profit claims
  - Product & Technology Constraints: UI areas, responsive UX, Python/React/SQL,
    XT.COM adapter isolation, credential hygiene, withdrawals out of scope
  - Market Sentiment Principles: emotion-free execution, external sentiment,
    adapters, traceability, control-plane authority, Dashboard component,
    composite score, Conservative Greed Principle, evaluation & history
  - Spec-Driven Development: incremental Spec Kit workflow, trading tests,
    specs as source of truth
  - Governance: amendment, versioning, compliance review
- Removed sections: N/A (template placeholders replaced)
- Follow-up TODOs: none
-->

# CryptoAutoTrading Constitution

## Core Principles

### I. Capital Protection First
Capital protection MUST take priority over profit seeking in every design,
configuration, and runtime decision. Features that increase return potential
MUST NOT weaken risk controls, session bounds, or fail-safe behavior.

**Rationale**: Preserving capital is the precondition for continued trading;
profit without protection is unacceptable product behavior.

### II. Simulation Before Real Money
The system MUST support both SIMULATION and REAL-MONEY modes. Development,
validation, strategy evaluation, and acceptance MUST begin in simulation.
Real-money trading is a separate later capability and MUST NEVER activate
automatically, by default, or as a silent side effect of configuration or
deployment.

**Rationale**: Simulation is the mandatory proving ground before capital risk.

### III. Controlled Trading Pipeline
Strategies MUST NEVER place orders directly. The required flow is:

Market Data → Strategy Engine → Trading Signal → Trading Controller →
Risk Manager → Execution Engine → Simulation or XT

Bypassing any stage of this pipeline is forbidden.

**Rationale**: Separation of signal generation from control, risk, and
execution keeps authority and auditability enforceable.

### IV. Controller and Risk Authority
The Trading Controller and Risk Manager MUST always retain authority to
reject strategy signals. Strategy output is advisory input only; rejection
is a first-class, expected outcome.

**Rationale**: Unfiltered strategy autonomy is incompatible with capital
protection.

### V. Explicit Session Boundaries
Every trading session MUST support explicit, enforceable boundaries including
at least:

- allocated capital
- position-size limit
- profit target
- maximum loss
- maximum number of trades
- trading-session duration
- strategy signal timeframe

Sessions MUST NOT run without these bounds defined and enforced.

**Rationale**: Bounded sessions make risk measurable and stoppable.

### VI. Net P&L Accounting
Session profit and loss MUST be based on NET P&L where possible, including
trading fees and slippage, not price movement alone.

**Rationale**: Gross price P&L misstates real outcomes and can encourage unsafe
decisions.

### VII. Decision Traceability
Every material trading decision MUST be traceable. The system MUST maintain
both a Trade Journal and a Decision Journal, including rejected signals and
the reason for each rejection.

**Rationale**: Without journals, risk behavior cannot be audited or improved.

### VIII. Fail Safe on Uncertainty
When critical data is missing, stale, or inconsistent, or when execution state
is uncertain, the system MUST fail safely: reject or suspend trading rather
than guess, interpolate critically, or continue as if healthy.

**Rationale**: Guessing under uncertainty risks uncontrolled capital loss.

### IX. Emergency Trading Stop
The system MUST provide an emergency trading stop that immediately halts new
trading activity under operator control.

**Rationale**: Operators need a decisive kill switch when conditions degrade.

### X. Intentional Simplicity
The application MUST remain intentionally simple and trackable. Prefer clear,
conventional designs over clever or opaque complexity. Complexity MUST be
justified by an explicit requirement.

**Rationale**: Simplicity improves correctness, auditability, and safe change.

### XI. Conventional Strategies First
Development MUST start with understandable, conventional trading strategies.
AI/ML strategies are future experimental features and, if introduced, MUST
obey exactly the same Trading Controller, Risk Manager, session bounds, and
journaling rules as conventional strategies.

**Rationale**: Familiar strategies are easier to validate; experiments must not
escape the control plane.

### XII. Evidence, Not Guarantees
Backtesting and simulation provide evidence, not guarantees of future
profitability. No UI copy, report, metric label, or marketing-facing text MAY
imply guaranteed profit.

**Rationale**: Overclaiming creates false confidence and unsafe user behavior.

## Product & Technology Constraints

### XIII. Primary UI Areas
The main UI MUST have exactly three primary areas:

- Dashboard
- Auto Trading
- Portfolio

New top-level primary areas MUST NOT be added without a constitutional
amendment.

**Rationale**: A fixed information architecture keeps the product trackable
and phone-usable.

### XIV. Responsive User Experience
All user-facing functionality MUST be responsive and usable from a phone as
well as desktop.

**Rationale**: Operators must be able to monitor and stop trading on mobile.

### XV. Technology Stack
- Backend MUST be Python.
- Frontend MUST be React.
- Persistence MUST be SQL-based. SQLite is acceptable for local development;
  PostgreSQL MAY be used later on a server.

**Rationale**: A constrained stack reduces accidental complexity and keeps the
system operable by a small team.

### XVI. Exchange Adapter Isolation
XT.COM is the first exchange. Exchange-specific implementation MUST be
isolated behind an exchange adapter so strategies, risk logic, and trading
control do NOT depend directly on XT APIs or XT-specific types.

**Rationale**: Adapter boundaries protect the control plane from exchange churn
and enable future venues without rewriting risk logic.

### XVII. Credential Hygiene
Exchange API credentials MUST remain backend-only. They MUST NEVER be
committed to Git or exposed to frontend code, client bundles, or public
configuration.

**Rationale**: Credential leakage enables unauthorized trading and fund risk.

### XVIII. Withdrawals Out of Scope
Withdrawal functionality is outside the trading integration and MUST NOT be
implemented as part of the core trading path.

**Rationale**: Narrowing scope reduces attack surface and operational risk.

## Market Sentiment Principles
 
### XIX. Remove User Emotion From Execution
The user's personal fear, greed, excitement, or subjective market feeling
MUST NOT be entered as a routine trading signal.

**Rationale**: Human emotion is the failure mode this product exists to avoid.

### XX. Measure Market Sentiment Independently
CryptoAutoTrading SHOULD independently measure broader market sentiment using external
data sources where legally and technically practical. Potential inputs MAY
include Crypto Fear & Greed indexes, cryptocurrency-specific sentiment, news
sentiment, social/community sentiment, market momentum, volatility, trading
volume/participation, and other validated public sentiment indicators.

**Rationale**: Collective market emotion is data; personal emotion is noise.

### XXI. Sentiment Provider Adapters
Prefer free APIs where suitable. Sentiment providers MUST be isolated behind
replaceable adapters so source changes do not rewrite strategies or risk
logic.

**Rationale**: Vendor lock-in and source fragility must not contaminate the
control plane.

### XXII. Sentiment Traceability
Raw sentiment source, timestamp, original value, and normalized value SHOULD
be preserved for traceability and later analysis. Historical sentiment used
during decisions MUST be stored so later comparison is possible among:

- strategy without sentiment
- strategy with sentiment
- strategy with conservative sentiment-aware exit rules

**Rationale**: Sentiment value is only as good as its audit trail and
comparative evaluation.

### XXIII. Sentiment Never Bypasses Control
Sentiment is an input to strategies and trading control. It MUST NEVER bypass
the Trading Controller or Risk Manager, place orders directly, or weaken
session bounds.

**Rationale**: Sentiment is advisory context, not an execution authority.

### XXIV. Dashboard Market Sentiment
The Dashboard MUST expose a clear Market Sentiment component so the user can
see the current state of market fear/greed and related signals.

**Rationale**: Visibility of measured sentiment replaces subjective guesswork.

### XXV. Explainable Composite Sentiment
The architecture MAY eventually calculate an explainable composite sentiment
score from multiple sources. Any composite MUST remain explainable and
traceable to underlying inputs.

**Rationale**: Opaque scores recreate the opacity problem sentiment is meant
to solve.

### XXVI. Conservative Greed Principle
CryptoAutoTrading SHOULD investigate a Conservative Greed Principle: when an existing
position is profitable and external market sentiment is unusually
optimistic/greedy, the system MAY favor securing an acceptable profit earlier
instead of trying to capture the final portion of a market rise.

This conservative-exit policy MUST NEVER be described as guaranteeing profit.
Its effectiveness MUST first be evaluated through backtesting and simulation
before any real-money reliance.

**Rationale**: Elevated market optimism may increase the risk of adverse
price movement or reduced future upside. Earlier profit realization is a
risk-management hypothesis that must be evaluated empirically, not a
prediction or promise.

### Philosophy
Remove the user's emotion from execution, measure the market's collective
emotion as data, and use strict risk and execution discipline.

## Spec-Driven Development

### XXVII. Incremental Spec Kit Workflow
Development MUST be incremental and spec-driven. Each meaningful feature
MUST progress through specification, clarification, planning, tasks,
consistency analysis, implementation, and verification.

**Rationale**: Spec-first delivery prevents silent scope drift and unsafe
shortcuts in trading-critical work.

### XXVIII. Trading-Critical Tests
Trading-critical functionality MUST have automated tests covering control,
risk rejection, session bounds, fail-safe behavior, and journaling where
applicable.

**Rationale**: Untested trading paths are unacceptable capital risk.

### XXIX. Specifications as Source of Truth
Specifications are the source of truth. Implementation MUST NOT silently
diverge from approved specs. When reality and the spec conflict, update the
spec through the amendment/clarification path before or with the code change.

**Rationale**: Silent drift destroys auditability and governance.

## Governance

This constitution supersedes informal conventions, ad-hoc shortcuts, and
conflicting local practices for CryptoAutoTrading.

### Amendment Procedure
1. Propose the change with rationale, affected principles, and migration
   impact (code, specs, tests, UX copy).
2. Update `.specify/memory/constitution.md` with concrete principle text
   (no unexplained placeholders).
3. Bump `CONSTITUTION_VERSION` using semantic versioning:
   - MAJOR: backward-incompatible removals or redefinitions of principles
   - MINOR: new principle/section or materially expanded guidance
   - PATCH: clarifications, wording, typos, non-semantic refinements
4. Set **Last Amended** to the amendment date (ISO `YYYY-MM-DD`).
5. Cascade updates into active feature specs, plans, and tasks when those
   artifacts conflict with the new text.

### Compliance Review
- Specs, plans, tasks, PRs, and reviews MUST verify alignment with this
  constitution.
- Trading pipeline, risk authority, simulation-first, credential hygiene,
  journaling, fail-safe, and no-guaranteed-profit rules are NON-NEGOTIABLE
  review gates.
- Unjustified complexity, direct strategy→exchange coupling, frontend
  credentials, or auto-activation of real-money mode MUST be rejected.

### Runtime Guidance
Use Spec Kit workflows (`/speckit-specify`, `/speckit-clarify`,
`/speckit-plan`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`)
for feature delivery. When guidance conflicts, this constitution wins.

**Version**: 1.0.0 | **Ratified**: 2026-08-08 | **Last Amended**: 2026-08-08
