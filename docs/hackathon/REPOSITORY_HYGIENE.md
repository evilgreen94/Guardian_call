# Repository Hygiene Review

No files were deleted during final freeze.

## KEEP_PUBLIC

`README.md`, `.env.example`, `Dockerfile`, `requirements.txt`, `requirements.deploy.txt`, `backend/`, `frontend/`, `scenarios/`, `tests/`, and current files under `docs/hackathon/`.

## KEEP_HISTORICAL

`PROJECT_CONTEXT.md`, `AGENTS.md`, `docs/threat-model/`, `docs/DEMO_SCRIPT_DRAFT.md`, `docs/SEVEN_DAY_PLAN.md`, `docs/HACKATHON_MVP.md`, `docs/ANTIGRAVITY_WORKFLOW.md`, and `docs/hackathon/DEVELOPMENT_LOG.md`. Historical Canary names in commits, tags, API contracts, and milestone records remain truthful.

## MOVE_TO_DOCS

`ANTIGRAVITY_START_PROMPT.md` is a development handoff artifact and could move under `docs/history/` after human review.

## IGNORE

`logs/`, Python caches, virtual environments, coverage output, local environment files, and OS metadata are already ignored. Blender backup files should be added to ignore rules if they remain local working artifacts.

## REMOVE_CANDIDATE

`guardian_presence_v01.blend1` is a Blender backup. `guardian_presence_v01.blend` is a source working file that may be better stored under `design/` or external artifact storage. Review screenshots and superseded drafts before removal; do not erase historical evidence automatically.

## DO_NOT_TOUCH

Untracked M1.3 threat-model, scenario, and test files are active research work. `.gcloudignore` affects deployment packaging. Both require separate owner review and were preserved.

## Recommended judge-facing root

```text
README.md
LICENSE (when the owner chooses one)
requirements.txt
requirements.deploy.txt
Dockerfile
.env.example
backend/
frontend/
docs/
scenarios/
tests/
```
