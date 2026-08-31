# Guardian Call Demo Script

Target duration: 3:35-3:50. Use only synthetic text. Confirm provider health before recording.

## 0:00-0:35 - Problem

**On screen:** Guardian at `/guardian/`.

**Narration:** "A convincing caller can know your name, provider, or account context. That knowledge still does not authenticate them. Guardian Call focuses on the moment the caller asks you to disclose, transfer, install, or approve something dangerous."

## 0:35-1:35 - Dangerous example

Submit this synthetic text through the real Guardian text control:

> I am Elena from the fictional Northbridge Bank fraud desk. A transfer is pending. Read me the six-digit verification code now so I can cancel it.

Wait for the real API response. Show the warning only if it is produced by the backend.

**Narration:** "Gemini extracts factual signals into a fixed schema. It does not decide whether this is safe and cannot authorize an intervention. The deterministic risk engine explains the risk, then KERN-3 decides whether the warning action is allowed."

## 1:35-2:15 - Authority boundary

**On screen:** Open `/visualizer/` and point to the KERN-3 authority panel and event timeline.

**Narration:** "This is the policy boundary. Internally, existing API and event contracts retain their historical Canary identifiers, but the public authority is KERN-3. A warning cannot execute without an allow decision."

Show the real sequence if present:

```text
INPUT_RECEIVED -> SIGNAL_DETECTED -> RISK_UPDATED
-> CANARY_EVALUATION -> ACTION_ALLOWED -> USER_WARNING
```

## 2:15-2:55 - Benign restraint

Return to Guardian and submit:

> I generated a sign-in code for my own account and entered it directly on the official website. I did not share it with anyone.

**Narration:** "A useful protection system must also show restraint. Guardian distinguishes a caller requesting a secret from a user completing a self-service action."

Only describe the result that actually appears.

## 2:55-3:25 - Google Cloud proof

Open `/health` and show the healthy Cloud Run service without exposing credentials.

**Narration:** "The FastAPI backend and both interfaces run together on Google Cloud Run. Gemini provides structured language extraction; deterministic code retains risk and policy authority."

## 3:25-3:50 - Close

**Narration:** "Guardian Call does not claim caller authentication or live carrier interception. It demonstrates a safer agentic pattern: language understanding without unchecked authority, explainable risk, and an explicit boundary before consequential action."

Do not present `?guardianVisualReview=1` states as backend decisions. They are labelled demo previews for visual review only.
