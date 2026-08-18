"""Deterministic pipeline coordinator for Guardian Call M0."""

from dataclasses import dataclass, field
from typing import List, Optional
from .actions import execute_warning_action
from .canary import CanaryPolicy
from .events import EventSink, EventType, GuardianEvent, InMemoryEventSink
from .extractor import ExtractionError, SignalExtractor
from .models import ActionType, CanaryDecision, PolicyDecision, RiskAssessment, ScamSignals
from .risk import RiskEngine


@dataclass(frozen=True)
class PipelineResult:
    """Outcome of processing signals or text through the Guardian Call pipeline."""
    signals: Optional[ScamSignals] = None
    risk_assessment: Optional[RiskAssessment] = None
    canary_decision: Optional[CanaryDecision] = None
    warning_event: Optional[GuardianEvent] = None
    events: List[GuardianEvent] = field(default_factory=list)
    error: Optional[ExtractionError] = None


class GuardianPipeline:
    """Coordinates the Guardian Call M0 evaluation pipeline."""

    def __init__(
        self,
        risk_engine: Optional[RiskEngine] = None,
        canary_policy: Optional[CanaryPolicy] = None,
        extractor: Optional[SignalExtractor] = None,
    ) -> None:
        self.risk_engine = risk_engine or RiskEngine()
        self.canary_policy = canary_policy or CanaryPolicy()
        self.extractor = extractor

    def process_text(
        self,
        text: str,
        event_sink: Optional[EventSink] = None,
    ) -> PipelineResult:
        """Process raw conversational text through Gemini extraction, Risk Engine, and Canary.

        Sequential Event Lifecycle on Success:
        1. INPUT_RECEIVED
        2. SIGNAL_DETECTED
        3. RISK_UPDATED
        4. CANARY_EVALUATION
        5. If ALLOW: ACTION_ALLOWED -> USER_WARNING
        6. If DENY:  ACTION_DENIED

        Sequential Event Lifecycle on Extraction Failure:
        1. INPUT_RECEIVED
        2. EXTRACTION_FAILED
        (Stops immediately; does not run Risk Engine or Canary)
        """
        sink = event_sink or InMemoryEventSink()

        # Step 1: Record that input text was received (sanitized metadata only)
        sink.emit(
            GuardianEvent(
                event_type=EventType.INPUT_RECEIVED,
                payload={"input_length": len(text), "input_type": "text"},
            )
        )

        if self.extractor is None:
            raise RuntimeError("GuardianPipeline requires a SignalExtractor to process text.")

        # Step 2: Attempt conversational signal extraction
        try:
            signals = self.extractor.extract_signals(text)
        except ExtractionError as err:
            # Extraction failure lifecycle: INPUT_RECEIVED -> EXTRACTION_FAILED
            # Stop immediately: do not construct empty ScamSignals, do not run Risk Engine, do not evaluate Canary.
            sink.emit(
                GuardianEvent(
                    event_type=EventType.EXTRACTION_FAILED,
                    payload={"error_type": err.error_type, "message": str(err)},
                )
            )
            all_events = sink.get_events() if isinstance(sink, InMemoryEventSink) else []
            return PipelineResult(
                signals=None,
                risk_assessment=None,
                canary_decision=None,
                warning_event=None,
                events=all_events,
                error=err,
            )

        # Step 3: Delegate to deterministic signal processing pipeline
        return self.process_signals(signals, event_sink=sink)

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

        # Step 1: Record that structured signals were detected/provided
        sink.emit(
            GuardianEvent(
                event_type=EventType.SIGNAL_DETECTED,
                payload={"signals": signals.to_dict()},
            )
        )

        # Step 2: Risk assessment via deterministic RiskEngine
        risk_assessment = self.risk_engine.evaluate(signals)
        sink.emit(
            GuardianEvent(
                event_type=EventType.RISK_UPDATED,
                payload=risk_assessment.to_dict(),
            )
        )

        # Step 3: Canary policy evaluation for WARN_USER
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

        # Step 4: Strict sequential execution based on Canary authority
        warning_event: Optional[GuardianEvent] = None

        if canary_decision.decision == PolicyDecision.ALLOW:
            sink.emit(
                GuardianEvent(
                    event_type=EventType.ACTION_ALLOWED,
                    payload={"action": ActionType.WARN_USER.value, "reason": canary_decision.reason},
                )
            )
            # Execute authorized warning action
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
            error=None,
        )
