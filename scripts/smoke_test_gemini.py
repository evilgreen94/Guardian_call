"""Manual smoke-test script for Guardian Call M0 live Gemini integration.

Executes real Gemini extraction against two synthetic test scenarios:
1. Fraudulent OTP exfiltration request (Scam)
2. Legitimate in-app OTP verification guidance (Benign)

Prints the complete pipeline state transitions and emitted event sequence.
"""

import json
import os
import sys
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian import (
    DEFAULT_GEMINI_MODEL,
    GeminiSignalExtractor,
    GuardianPipeline,
    InMemoryEventSink,
)


def run_scenario(pipeline: GuardianPipeline, title: str, text_input: str) -> None:
    print("=" * 70)
    print(f"SCENARIO: {title}")
    print("=" * 70)
    print(f"INPUT TEXT:\n  \"{text_input}\"\n")

    sink = InMemoryEventSink()
    result = pipeline.process_text(text_input, event_sink=sink)

    if result.error:
        print(f"[ERROR] Extraction Failed: {result.error}")
        print("\nEmitted Events:")
        for event in sink.get_events():
            print(f"  - {event.event_type}: {event.payload}")
        print("\n" + "-" * 70 + "\n")
        return

    # 1. Extracted Signals
    print("1. EXTRACTED SIGNALS (Gemini):")
    if result.signals:
        print(f"   {json.dumps(result.signals.to_dict(), indent=4)}")

    # 2. Risk Assessment
    print("\n2. RISK ASSESSMENT (Risk Engine):")
    if result.risk_assessment:
        print(f"   Level: {result.risk_assessment.level.value}")
        print(f"   Contributing Signals: {result.risk_assessment.contributing_signals}")
        print("   Reasons:")
        for r in result.risk_assessment.reasons:
            print(f"     • {r}")

    # 3. Canary Policy Decision
    print("\n3. CANARY POLICY DECISION:")
    if result.canary_decision:
        print(f"   Action:   {result.canary_decision.action.value}")
        print(f"   Decision: {result.canary_decision.decision.value}")
        print(f"   Reason:   {result.canary_decision.reason}")

    # 4. User Warning
    print("\n4. USER WARNING (Action Execution):")
    if result.warning_event:
        payload = result.warning_event.payload
        print(f"   Headline:   {payload.get('headline')}")
        print(f"   Severity:   {payload.get('severity')}")
        print(f"   Directives: {payload.get('directives')}")
    else:
        print("   [No warning issued - Action Denied or not authorized]")

    # 5. Emitted Event Lifecycle Sequence
    print("\n5. EMITTED EVENT LIFECYCLE SEQUENCE:")
    events = sink.get_events()
    for idx, event in enumerate(events, 1):
        print(f"   [{idx}] {event.event_type}")

    print("\n" + "-" * 70 + "\n")


def main() -> None:
    api_key_present = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    if not api_key_present:
        print("[ERROR] GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set.", file=sys.stderr)
        print("Please ensure the environment variable is exported in your session.", file=sys.stderr)
        sys.exit(1)

    model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    print(f"Initializing GeminiSignalExtractor with model: {model_name}\n")

    try:
        extractor = GeminiSignalExtractor()
    except Exception as e:
        print(f"[ERROR] Failed to initialize GeminiSignalExtractor: {e}", file=sys.stderr)
        sys.exit(1)

    pipeline = GuardianPipeline(extractor=extractor)

    # Scenario 1: Fraudulent OTP Theft Request (Synthetic)
    scam_text = (
        "Hola, le llamamos del departamento de seguridad del Banco. Detectamos un movimiento sospechoso "
        "en su cuenta. Le acabamos de enviar un código de seis dígitos por SMS para cancelar la operación. "
        "Por favor dígame el código de inmediato para proteger su dinero."
    )
    run_scenario(pipeline, "Fraudulent OTP Exfiltration (Scam)", scam_text)

    # Scenario 2: Legitimate In-App OTP Guidance (Synthetic)
    legit_text = (
        "Estimado cliente, para confirmar la activación de su nueva tarjeta desde nuestra aplicación oficial, "
        "le enviamos un código de seguridad. Por favor ingrese ese código directamente en la pantalla de su app. "
        "Recuerde que ningún empleado de soporte le solicitará que revele este código por teléfono."
    )
    run_scenario(pipeline, "Legitimate In-App OTP Guidance (Benign)", legit_text)


if __name__ == "__main__":
    main()
