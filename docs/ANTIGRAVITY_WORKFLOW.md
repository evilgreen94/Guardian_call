# Antigravity Workflow

## First session

Open the repository folder as an Antigravity workspace.

Before asking the agent to write code, give it this task:

```text
Read PROJECT_CONTEXT.md and AGENTS.md completely.

Do not modify files yet.

Summarize:
1. the product thesis;
2. the canonical architecture;
3. M0;
4. architectural constraints;
5. privacy constraints;
6. what you believe the first coding task should be.

Flag any contradictions before proceeding.
```

Review its answer before allowing implementation.

---

## Recommended working mode

For architectural work, unfamiliar implementation work, or changes touching several files:
- use a planning-oriented agent mode;
- review the plan before execution.

For small, obvious changes:
- direct execution is acceptable.

---

## First implementation prompt

After the orientation step:

```text
Implement only the deterministic domain skeleton for M0.

Do NOT connect Gemini yet.

Create the minimum domain models and code required for:
- structured scam signals;
- RiskLevel;
- RiskAssessment;
- CanaryDecision;
- Guardian events;
- a deterministic Risk Engine;
- a basic Canary policy for warn_user.

Add tests.

The following synthetic signal must lead to CRITICAL risk:

otp_request=true
identity_claim="bank"
identity_verified=false
urgency=true
financial_context=true

Do not add frontend, persistence, Cloud services, audio, VoIP or extra agents.

Show me the plan before changing files.
```

---

## Second implementation prompt

Only after deterministic tests pass:

```text
Add a Gemini-backed text signal extractor behind a clean interface.

Requirements:
- Gemini returns structured signals matching the existing domain model.
- Deterministic Risk Engine and Canary logic must remain independent of Gemini.
- Use environment variables for credentials.
- Do not commit secrets.
- Add one synthetic integration test or a mocked contract test.
- Preserve existing tests.

Before editing, show the files you expect to change and why.
```

---

## Review prompt after each milestone

```text
Review the current implementation against PROJECT_CONTEXT.md and AGENTS.md.

Check specifically for:
- architectural boundary violations;
- unnecessary complexity;
- privacy issues;
- opaque risk logic;
- untested behavior;
- fake or hardcoded observability;
- scope creep beyond the current milestone.

Do not change code yet. Return findings ordered by severity.
```

---

## Important

Antigravity is allowed to be proactive, but Guardian Call should not become an experiment in autonomous code generation.

Human review remains part of the workflow.

If the agent proposes a major architectural change, record the decision as an ADR before implementation.
