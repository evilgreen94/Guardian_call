# Guardian Call Cloud Run Deployment Evidence

## Verified deployment identity

| Field | Value |
|---|---|
| Google Cloud project | `guardian-call-hackathon` |
| Cloud Run service | `guardian-stable` |
| Region | `europe-west1` |
| Public service URL | `https://guardian-stable-601044791798.europe-west1.run.app` |
| Guardian UI | `/guardian/` |
| KERN-3 visualizer | `/visualizer/` |
| Health | `/health` |

The known recovered healthy revision before the final local UI freeze was `guardian-stable-00007-zp9`. This document does not claim that the current uncommitted frontend and documentation changes are deployed, and it does not claim a later revision without fresh verification.

## Runtime

The service runs `backend.server:app` on Cloud Run and serves the API plus both static frontend surfaces from one container. `/` redirects to `/guardian/`.

The primary Guardian dependencies are:

- `POST /api/v1/analyze` for canonical M0 text analysis.
- `POST /api/v1/experimental/stt` for bounded browser audio transcription; the resulting transcript is then sent to `/api/v1/analyze`.

The KERN-3 technical visualizer additionally uses `POST /api/v1/experimental/v2/turn` and process-local in-memory session state.

## Credential handling

The runtime reads `GEMINI_API_KEY` or `GOOGLE_API_KEY` from the process environment. The Cloud Run service receives the Gemini credential from Secret Manager. Secret values must never be baked into images, frontend assets, documentation, shell history, or repository files.

## Current model

The stable M0 extractor default is `gemini-3.6-flash`, unless `GEMINI_MODEL` explicitly overrides it. The health route reports the effective model name and whether a key is configured, never the key value.

## Deployment boundary

No Cloud Run deployment is part of the final UI/documentation freeze. A later deployment must preserve the existing project, service name, region, environment variables, secret reference, and unrelated Cloud Run settings. The exact deployed revision and traffic state must be read back after deployment before updating this evidence.

## Read-only smoke routes

```text
GET /
GET /guardian/
GET /visualizer/
GET /health
```

Provider-backed smoke tests should use only synthetic benign and scam fixtures and must never print credentials or private transcripts.
