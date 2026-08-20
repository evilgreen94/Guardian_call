"""Deterministic pipeline coordinator for Guardian Call M0."""

from dataclasses import dataclass
from typing import List, Optional

from .actions import execute_warning_action
from .agent import SignalExtractionError, extract_signals
from .canary import CanaryPolicy
from .events import EventSink, EventType, GuardianEvent, InMemoryEventSink
from .models import (
    ActionType,
    CanaryDecision,
    PolicyDecision,
    RiskAssessment,
    RiskLevel,
    ScamSignals,
)
from .risk import RiskEngine


@dataclass(frozen=True)
class PipelineResult:
    """Outcome of processing signals through the deterministic M0 pipeline."""
    signals: ScamSignals
    risk_assessment: RiskAssessment
    canary_decision: CanaryDecision
    warning_event: Optional[GuardianEvent]
    events: List[GuardianEvent]


class GuardianPipeline:
    """Coordinates the deterministic Guardian Call M0 evaluation pipeline."""

    def __init__(
        self,
        risk_engine: Optional[RiskEngine] = None,
        canary_policy: Optional[CanaryPolicy] = None,
    ) -> None:
        self.risk_engine = risk_engine or RiskEngine()
        self.canary_policy = canary_policy or CanaryPolicy()

    def _act_on_risk_assessment(
        self,
        signals: ScamSignals,
        risk_assessment: RiskAssessment,
        sink: EventSink,
    ) -> PipelineResult:
        """Private helper to execute Canary evaluation, actions, and package PipelineResult."""
        canary_decision = self.canary_policy.evaluate_action(
            risk_assessment=risk_assessment,
            action=ActionType.WARN_USER,
        )
        sink.emit(
            GuardianEvent(
                event_type=EventType.CANARY_EVALUATION,
                payload=canary_decision.to_dict(),
            )
        )

        warning_event: Optional[GuardianEvent] = None

        if canary_decision.decision == PolicyDecision.ALLOW:
            sink.emit(
                GuardianEvent(
                    event_type=EventType.ACTION_ALLOWED,
                    payload={"action": ActionType.WARN_USER.value, "reason": canary_decision.reason},
                )
            )
            warning_event = execute_warning_action(
                canary_decision=canary_decision,
                risk_assessment=risk_assessment,
                event_sink=sink,
            )
        else:
            sink.emit(
                GuardianEvent(
                    event_type=EventType.ACTION_DENIED,
                    payload={"action": ActionType.WARN_USER.value, "reason": canary_decision.reason},
                )
            )

        all_events = sink.get_events() if isinstance(sink, InMemoryEventSink) else []

        return PipelineResult(
            signals=signals,
            risk_assessment=risk_assessment,
            canary_decision=canary_decision,
            warning_event=warning_event,
            events=all_events,
        )

    def process_signals(
        self,
        signals: ScamSignals,
        event_sink: Optional[EventSink] = None,
    ) -> PipelineResult:
        """Process structured scam signals through Risk Engine, Canary, and Action execution.

        Sequential Event Lifecycle:
        1. SIGNAL_DETECTED
        2. RISK_UPDATED
        3. CANARY_EVALUATION
        4. If ALLOW: ACTION_ALLOWED -> USER_WARNING
        5. If DENY:  ACTION_DENIED
        """
        sink = event_sink or InMemoryEventSink()

        sink.emit(
            GuardianEvent(
                event_type=EventType.SIGNAL_DETECTED,
                payload={"signals": signals.to_dict()},
            )
        )

        risk_assessment = self.risk_engine.evaluate(signals)
        sink.emit(
            GuardianEvent(
                event_type=EventType.RISK_UPDATED,
                payload=risk_assessment.to_dict(),
            )
        )

        return self._act_on_risk_assessment(signals, risk_assessment, sink)

    def process_text(
        self,
        text: str,
        event_sink: Optional[EventSink] = None,
    ) -> PipelineResult:
        """Process raw conversational text input through Gemini signal extraction and Guardian M0 pipeline.

        Privacy rule: Only text length is emitted in INPUT_RECEIVED payload; raw text is never logged.
        Fail-safe rule: On SignalExtractionError, bypass RiskEngine and assign synthetic HIGH risk.
        """
        sink = event_sink or InMemoryEventSink()

        sink.emit(
            GuardianEvent(
                event_type=EventType.INPUT_RECEIVED,
                payload={"text_length": len(text) if text is not None else 0},
            )
        )

        if not text or not text.strip():
            # Empty input is processed as baseline ScamSignals() yielding NORMAL risk
            empty_signals = ScamSignals()
            sink.emit(
                GuardianEvent(
                    event_type=EventType.SIGNAL_DETECTED,
                    payload={"signals": empty_signals.to_dict()},
                )
            )
            risk_assessment = self.risk_engine.evaluate(empty_signals)
            sink.emit(
                GuardianEvent(
                    event_type=EventType.RISK_UPDATED,
                    payload=risk_assessment.to_dict(),
                )
            )
            return self._act_on_risk_assessment(empty_signals, risk_assessment, sink)

        try:
            signals = extract_signals(text)
        except SignalExtractionError:
            # Fail-safe posture on extraction error
            sink.emit(
                GuardianEvent(
                    event_type=EventType.SIGNAL_EXTRACTION_FAILED,
                    payload={"reason": "signal_extraction_failed"},
                )
            )
            fallback_signals = ScamSignals()
            risk_assessment = RiskAssessment(
                level=RiskLevel.HIGH,
                reasons=["Unable to analyze conversation content; defaulting to cautious posture"],
                contributing_signals=["extraction_failed"],
            )
            sink.emit(
                GuardianEvent(
                    event_type=EventType.RISK_UPDATED,
                    payload=risk_assessment.to_dict(),
                )
            )
            return self._act_on_risk_assessment(fallback_signals, risk_assessment, sink)

        sink.emit(
            GuardianEvent(
                event_type=EventType.SIGNAL_DETECTED,
                payload={"signals": signals.to_dict()},
            )
        )
        risk_assessment = self.risk_engine.evaluate(signals)
        sink.emit(
            GuardianEvent(
                event_type=EventType.RISK_UPDATED,
                payload=risk_assessment.to_dict(),
            )
        )

        return self._act_on_risk_assessment(signals, risk_assessment, sink)

    def process_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        event_sink: Optional[EventSink] = None,
    ) -> PipelineResult:
        """Process image/screenshot input through Google ADK vision agent and Guardian pipeline."""
        sink = event_sink or InMemoryEventSink()

        sink.emit(
            GuardianEvent(
                event_type=EventType.IMAGE_RECEIVED,
                payload={"image_size_bytes": len(image_bytes) if image_bytes else 0, "mime_type": mime_type},
            )
        )

        from .vision_agent import VisionOcrError, process_image as vision_process_image

        ocr_result = None
        if image_bytes:
            try:
                ocr_result = vision_process_image(image_bytes, mime_type=mime_type)
            except VisionOcrError:
                ocr_result = None

        if ocr_result:
            sink.emit(
                GuardianEvent(
                    event_type=EventType.IMAGE_PROCESSED_OCR,
                    payload={
                        "text_length": len(ocr_result.extracted_text),
                        "visual_manipulation_suspected": ocr_result.visual_manipulation_suspected,
                        "channel_detected": ocr_result.channel_detected,
                    },
                )
            )
            extracted_text = ocr_result.extracted_text
        else:
            extracted_text = ""

        return self.process_text(extracted_text, event_sink=sink)

