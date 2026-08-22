# Lab Porting Matrix

Use the experimental branch as a source, not as an architecture.

| Lab component | Decision | Target | Reason / conditions |
|---|---|---|---|
| `backend/server.py` | ADAPT | minimal server module | Keep FastAPI/SSE concepts; wire to canonical M0 core |
| `frontend/visualizer/*` | ADAPT | `frontend/visualizer/` | Keep event/UI plumbing; remove Guardian 360, image, inbox controls |
| `backend/guardian/trusted_circle.py` | REWRITE / ADAPT LATER | canonical actions/policy | Only after multi-turn; event-first, no real delivery required |
| `scenarios/bank_otp_scam.json` | ADAPT | canonical scenarios | Keep as demo scenario |
| `scenarios/legitimate_bank_notification.json` | ADAPT | canonical scenarios | Keep as false-positive control |
| `scenarios/bank_secure_vault_scam.json` | ADAPT | canonical scenarios | Keep transfer scam if clean |
| `scenarios/tech_support_anydesk_scam.json` | ADAPT | canonical scenarios | Keep remote-access demo |
| remaining scenario catalogue | DO NOT PORT NOW | parking | Scope breadth not needed |
| `backend/guardian/email_listener.py` | DO NOT PORT | parking | Not Guardian Call MVP |
| `backend/guardian/vision_agent.py` | DO NOT PORT | parking | Not Guardian Call MVP |
| Guardian 360 docs/code | DO NOT PORT | parking | Future product direction |
| lab `pipeline.py` | DO NOT PORT AS REPLACEMENT | — | Main pipeline is canonical |
| lab extraction fallback semantics | DO NOT PORT | — | Must preserve explicit extraction failure |
| lab hard-coded model config | DO NOT PORT | — | Keep model configurable |
| Dockerfile | ADAPT LATER | root | Useful for Cloud Run after local demo is stable |
