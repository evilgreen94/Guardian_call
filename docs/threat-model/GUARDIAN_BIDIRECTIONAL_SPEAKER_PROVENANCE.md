# Guardian Bidirectional Speaker Provenance

Status: future production requirement, not implemented in the current browser demo.

## Hard Requirement

VOICE INPUT != SPEAKER IDENTITY.

Guardian and Canary must eventually process both sides of a live call because
longitudinal reasoning benefits from observing:

- what the remote interlocutor requests;
- how the protected user responds;
- whether the protected user begins complying;
- whether pressure escalates after resistance;
- whether the protected user is about to disclose, transfer, install, or grant access.

Speaker identity and speaker role must not be inferred from transcript language.

If a remote speaker says "Soy tu hijo", that does not make the turn USER, and
it does not authenticate a family identity. The statement is only an unverified
identity claim. Knowledge and claimed identity are not authentication.

## Required Future Provenance Values

- USER
- CALLER
- THIRD_PARTY_OR_UNKNOWN

The preferred production trust source is a telephony provider or call gateway
with separated inbound and outbound audio channels or tracks.

## Conceptual Production Flow

```text
LOCAL / protected-user audio track
    -> STT
    -> speaker provenance = USER
    -> TurnText

REMOTE / inbound audio track
    -> STT
    -> speaker provenance = CALLER
    -> TurnText
```

Both streams enter the same longitudinal conversation/session in temporal
order. The extractor may interpret what is being said. It must not authenticate
who is speaking from semantic content.

## Why Bidirectionality Matters

Example 1:

```text
CALLER:
Tell me the six-digit code you just received.
```

Expected semantic meaning: USER is being requested to DISCLOSE OTP to CALLER.

Example 2:

```text
USER:
Okay, I'll tell you the code.
```

This user utterance is valuable evidence: the protected user is progressing
toward a sensitive disclosure. It should not be discarded merely because it was
spoken by USER.

Example 3:

```text
CALLER:
I'm your son.
```

Channel provenance remains CALLER. The family identity statement is only an
unverified identity claim.

Example 4:

```text
USER:
I'm opening my banking app now.
```

Speaker provenance USER may help longitudinal reasoning determine that the
protected user is progressing toward a sensitive action.

## Rejected Trust Boundary

This architecture is explicitly rejected as a trusted source of speaker role:

```text
mixed audio
    -> STT
    -> LLM guesses speaker
    -> trusted USER/CALLER role
```

Diarization may be useful as an assistive or fallback signal in a future
prototype, but it is not an authentication or trust boundary. The preferred
production guarantee remains channel or track provenance.

## Demo Fallback, Future Only

If bidirectional behavior is needed before real telephony integration, a
controlled browser demo may use explicit provenance controls such as:

```text
[ CALLER SPEAKING ]
[ USER SPEAKING ]
```

Each captured or transcribed utterance would enter the same canonical TurnText
and M2 path with user-selected provenance. This is acceptable only as an
explicit demo mechanism. It must never be presented as automatic speaker
recognition.

## Single-Submission Shared Session Requirement

Future Guardian and Canary integration must preserve:

```text
one utterance
    -> one canonical submission
    -> one longitudinal state transition
```

If Guardian and Canary display the same conversation simultaneously, they must
not independently submit the same utterance.

Preferred future architecture:

```text
one producer/submission path
    +
shared session_id
    +
read-only observer/event surface for the second UI
```

This prevents duplicated source turns, M2 turns, risk transitions, policy
events, and Canary evaluations.

## Telephony Scope

Full live phone-call interception or device-level integration is not a current
delivery requirement.

Current implemented demo path:

```text
browser microphone / text
    -> STT
    -> TurnText
    -> M2.5
    -> Canary
    -> Guardian
```

Future production architecture:

```text
Phone / VoIP call
    -> telephony provider or call gateway
    -> separated audio streams
    -> STT
    -> trusted speaker provenance
    -> same TurnText pipeline
```

Do not fake device-level phone interception in the hackathon demo.
