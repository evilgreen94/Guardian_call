# Consolidate Lab Into Hackathon MVP

Port only useful infrastructure from the experimental lab branch into canonical main.

## Steps

1. Read:
   - `PROJECT_CONTEXT.md`
   - `AGENTS.md`
   - `.agents/rules/hackathon-scope-freeze.md`

2. Inspect current main before any edits:
   - current backend architecture;
   - current M0 tests;
   - current Gemini extractor;
   - current event semantics.

3. Inspect the experimental lab branch/source.

4. Produce a file-by-file matrix with exactly one classification:
   - `REUSE AS IS`
   - `ADAPT`
   - `REWRITE`
   - `DO NOT PORT`

5. For every `ADAPT` or `REWRITE`, explain:
   - which useful behavior is being retained;
   - which lab behavior violates main architecture;
   - target file in main;
   - tests required.

6. List proposed dependencies. For each dependency state:
   - why it is needed now;
   - whether it is direct or transitive;
   - whether standard library can reasonably replace it.

7. Stop for human approval.

8. After approval, implement only:
   - FastAPI health endpoint;
   - text analysis endpoint using existing `GeminiSignalExtractor` and `GuardianPipeline`;
   - SSE stream of real Guardian events;
   - minimal visualizer consuming those events.

9. Explicitly do not port:
   - IMAP/email;
   - vision/image;
   - Guardian 360;
   - audio;
   - multi-turn state;
   - Trusted Circle delivery;
   - Cloud deployment.

10. Run:
   - all existing M0 tests unchanged;
   - new server endpoint tests;
   - new SSE/event tests.

11. Report:
   - changed files;
   - dependencies added;
   - full test count;
   - exact browser demo steps;
   - known limitations.

12. Do not start the next milestone automatically.
