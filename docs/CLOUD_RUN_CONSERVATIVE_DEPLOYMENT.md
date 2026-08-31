# Guardian Call Conservative Cloud Run Deployment

This document prepares the first conservative Cloud Run deployment. It does
not change application semantics and does not introduce Vertex AI.
It does not prove parity with any currently running Cloud Run revision; that
must be established separately from deployment metadata or a fresh deployment
from an exact Git SHA.

## Runtime

- Service: `guardian-stable`
- Application: `backend.server:app`
- Container port: `8080`
- Uvicorn bind: `0.0.0.0:${PORT:-8080}`
- Frontends:
  - `/` redirects to `/guardian/`
  - `/guardian/` serves the protected-user Guardian demo UI
  - `/visualizer/` serves the technical Canary/observability visualizer
- Guardian demo API dependencies:
  - `/api/v1/experimental/v2/turn`
  - `/api/v1/experimental/stt`

## Required Secret

The application reads the current provider key from either:

- `GEMINI_API_KEY`
- `GOOGLE_API_KEY`

Do not bake keys into the image, Dockerfile, frontend, or repository. For Cloud
Run, inject the key with Secret Manager.

Prepare the secret during deployment setup:

```bash
printf '%s' "$GEMINI_API_KEY" | gcloud secrets create guardian-gemini-api-key \
  --data-file=- \
  --replication-policy=automatic
```

For later rotations:

```bash
printf '%s' "$GEMINI_API_KEY" | gcloud secrets versions add guardian-gemini-api-key \
  --data-file=-
```

## Optional Model Configuration

The application already supports these optional environment variables:

- `GEMINI_V2_MODEL`
- `GEMINI_STT_MODEL`
- `GEMINI_MODEL`

Do not set them unless we intentionally want to override the application
defaults during deployment.

## In-Memory Session Constraint

The experimental V2 session state is process-local and in-memory.

For the hackathon demo deployment, configure Cloud Run with:

```text
--max-instances=1
```

This means:

- active sessions are lost on container restart;
- concurrent sessions only share state inside the same running instance;
- this is acceptable for the hackathon demo;
- this is not the intended production persistence architecture.

## Proposed Build And Deploy Commands

Select the Google Cloud project and region before deployment. Region is not
guessed by this document.

```bash
gcloud config set project PROJECT_ID
gcloud config set run/region REGION
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/guardian/guardian-stable:latest
gcloud run deploy guardian-stable \
  --image REGION-docker.pkg.dev/PROJECT_ID/guardian/guardian-stable:latest \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --max-instances 1 \
  --min-instances 0 \
  --memory 512Mi \
  --cpu 1 \
  --set-secrets GEMINI_API_KEY=guardian-gemini-api-key:latest
```

If using Artifact Registry for the first time, create the repository before
`gcloud builds submit`:

```bash
gcloud artifacts repositories create guardian \
  --repository-format=docker \
  --location=REGION \
  --description="Guardian Call demo images"
```

## Local Container Smoke

If Docker is available locally:

```bash
docker build -t guardian-stable:local .
docker run --rm -p 8080:8080 --name guardian-stable-smoke guardian-stable:local
```

Then verify without provider-backed endpoints:

```bash
curl -i http://127.0.0.1:8080/health
curl -i http://127.0.0.1:8080/guardian/
curl -i http://127.0.0.1:8080/visualizer/
curl -i http://127.0.0.1:8080/
```
