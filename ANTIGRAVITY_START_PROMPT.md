# Antigravity — Start Prompt

Paste this into the Agent after adding the hackathon scope pack to the repository.

---

We are now in Guardian Call hackathon scope-freeze mode.

Read completely before proposing any change:

- `PROJECT_CONTEXT.md`
- `AGENTS.md`
- `.agents/rules/hackathon-scope-freeze.md`
- `docs/HACKATHON_MVP.md`
- `docs/PORTING_MATRIX.md`
- `docs/SEVEN_DAY_PLAN.md`

The experimental `lab-splurtch-dev-antigravity` branch/source is a research source only. Do NOT merge it into main and do NOT replace the stable M0 architecture.

First task: prepare Day 1 consolidation.

Goal:

`Browser text input → existing GeminiSignalExtractor → existing GuardianPipeline → real domain events → SSE → minimal browser visualizer`

Before modifying any file:

1. inspect main;
2. inspect lab source;
3. produce a file-by-file porting matrix using only:
   - REUSE AS IS
   - ADAPT
   - REWRITE
   - DO NOT PORT
4. list every proposed dependency and justify it;
5. identify any lab behavior that conflicts with canonical main semantics;
6. show the exact files you propose to create/modify;
7. state the tests you will add;
8. stop for approval.

Do not implement until approved.

Explicitly out of scope for this task:
email, IMAP, vision, OCR, Guardian 360, audio, multi-turn state, real Trusted Circle delivery, Cloud deployment, mobile app, additional agents.
