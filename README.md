# Guardian Call

Agentic protection against conversational phone scams.

## Start here

1. Read `PROJECT_CONTEXT.md`.
2. Coding agents must also follow `AGENTS.md`.
3. Current milestone: **M0 — Text Detection**.

## Current demo surfaces

- `/guardian/` is the intended protected-user demo UI.
- `/visualizer/` is the technical Canary/observability visualizer.
- `/` redirects to `/guardian/`.

The Guardian UI uses the current experimental demo endpoints:

- `/api/v1/experimental/v2/turn`
- `/api/v1/experimental/stt`

The STT path is a controlled browser/demo path, not direct phone-call
interception or production telephony integration.

## Current target

```text
Text → Gemini → Signal → Risk Engine → Canary → USER_WARNING
```

The project deliberately starts small. The architecture can grow only after this pipeline works reliably.
