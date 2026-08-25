"""Deterministic pipeline coordinator for Guardian Call M0."""

from dataclasses import dataclass
from typing import List, Optional

from .actions import execute_warning_action
from .agent import SignalExtractionError, extract_signals
from .canary import CanaryPolicy
from .events import EventType, GuardianEvent, InMemoryEventSink
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
        gemma_guardrail: Optional[Any] = None,
    ) -> None:
        from .gemma_guardrail import GemmaGuardrail
        self.risk_engine = risk_engine or RiskEngine()
        self.canary_policy = canary_policy or CanaryPolicy()
        self.gemma_guardrail = gemma_guardrail or GemmaGuardrail()

    def _act_on_risk_assessment(
        self,
        signals: ScamSignals,
        risk_assessment: RiskAssessment,
        sink: InMemoryEventSink,
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

        # Evaluate and execute NOTIFY_TRUSTED_CIRCLE under Canary policy
        trusted_decision = self.canary_policy.evaluate_action(
            risk_assessment=risk_assessment,
            action=ActionType.NOTIFY_TRUSTED_CIRCLE,
        )
        if trusted_decision.decision == PolicyDecision.ALLOW:
            from .trusted_circle import execute_trusted_circle_notification
            execute_trusted_circle_notification(
                canary_decision=trusted_decision,
                risk_assessment=risk_assessment,
                event_sink=sink,
            )

        # Evaluate and execute ACTIVATE_SCAMTRAP under Canary policy
        scamtrap_decision = self.canary_policy.evaluate_action(
            risk_assessment=risk_assessment,
            action=ActionType.ACTIVATE_SCAMTRAP,
        )
        if scamtrap_decision.decision == PolicyDecision.ALLOW:
            sink.emit(
                GuardianEvent(
                    event_type=EventType.SCAMTRAP_ACTIVATED,
                    payload={
                        "action": ActionType.ACTIVATE_SCAMTRAP.value,
                        "decision": scamtrap_decision.decision.value,
                        "reason": scamtrap_decision.reason,
                    },
                )
            )
            from .scamtrap import run_scamtrap_agent
            intel = run_scamtrap_agent(getattr(signals, "raw_text", "") or "Threat detected")
            sink.emit(
                GuardianEvent(
                    event_type=EventType.INTELLIGENCE_EXTRACTED,
                    payload=intel.model_dump(),
                )
            )

        all_events = sink.get_events()

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
        event_sink: Optional[InMemoryEventSink] = None,
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
        event_sink: Optional[InMemoryEventSink] = None,
        is_first_turn: bool = True,
        force_escalate: Optional[bool] = None,
    ) -> PipelineResult:
        """Process raw conversational text input through Gemini signal extraction and Guardian M0 pipeline.

        Privacy rule: Only text length is emitted in INPUT_RECEIVED payload; raw text is never logged.
        Fail-safe rule: On SignalExtractionError, bypass RiskEngine and assign synthetic HIGH risk.
        Gate rule: is_first_turn defaults to True so single-shot callers (M0 tests, scenario runner,
        /api/v1/analyze without session context) always reach Gemini exactly like before this gate
        existed. force_escalate lets a caller that tracks real CallSession state (guardian.session)
        hand in an escalate/skip decision already computed from the accumulated transcript plus the
        periodic safety net, instead of this method recomputing a single-turn-only decision.
        """
        sink = event_sink or InMemoryEventSink()

        sink.emit(
            GuardianEvent(
                event_type=EventType.INPUT_RECEIVED,
                payload={"text_length": len(text) if text is not None else 0},
            )
        )

        if text and text.strip():
            gemma_res = self.gemma_guardrail.evaluate(text)
            sink.emit(
                GuardianEvent(
                    event_type=EventType.GEMMA_GUARDRAIL_EVALUATED,
                    payload=gemma_res.to_dict(),
                )
            )

            if gemma_res.prompt_injection_attempt:
                sink.emit(
                    GuardianEvent(
                        event_type=EventType.PROMPT_INJECTION_DETECTED,
                        payload={
                            "injection_type": gemma_res.injection_type,
                            "reason": gemma_res.reason,
                        },
                    )
                )
                from .signals import create_signals
                injection_signals = create_signals(
                    prompt_injection_attempt=True,
                    injection_type=gemma_res.injection_type,
                )
                sink.emit(
                    GuardianEvent(
                        event_type=EventType.SIGNAL_DETECTED,
                        payload={"signals": injection_signals.to_dict()},
                    )
                )
                risk_assessment = self.risk_engine.evaluate(injection_signals)
                sink.emit(
                    GuardianEvent(
                        event_type=EventType.RISK_UPDATED,
                        payload=risk_assessment.to_dict(),
                    )
                )
                return self._act_on_risk_assessment(injection_signals, risk_assessment, sink)

        if text and text.strip():
            from .signals import should_escalate_to_gemini
            escalate = (
                force_escalate
                if force_escalate is not None
                else should_escalate_to_gemini(text, is_first_turn=is_first_turn)
            )
            if not escalate:
                sink.emit(
                    GuardianEvent(
                        event_type=EventType.GATE_SKIPPED,
                        payload={"reason": "no_risk_vocabulary_detected"},
                    )
                )
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

            sink.emit(
                GuardianEvent(
                    event_type=EventType.GATE_ESCALATED,
                    payload={"reason": "first_turn" if is_first_turn else "risk_vocabulary_detected"},
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
        event_sink: Optional[InMemoryEventSink] = None,
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

        result = self.process_text(extracted_text, event_sink=sink)

        from .signals import text_keyword_flags
        flags = text_keyword_flags(extracted_text)

        if ocr_result and (
            ocr_result.suspicious_domain_detected
            or ocr_result.special_offer_detected
            or ocr_result.countdown_timer_detected
            or ocr_result.visual_manipulation_suspected
            or ocr_result.sender_email
            or flags["service_cancellation_threat"]
            or flags["urgency"]
            or flags["subscription_fee_claim"]
        ):
            from .signals import create_signals
            merged_signals = create_signals(
                identity_claim=result.signals.identity_claim or (ocr_result.channel_detected if ocr_result.channel_detected != "unknown" else None),
                identity_verified=result.signals.identity_verified,
                financial_context=result.signals.financial_context or flags["financial_context"],
                urgency=result.signals.urgency or ocr_result.countdown_timer_detected or flags["urgency"],
                secrecy_request=result.signals.secrecy_request,
                otp_request=result.signals.otp_request,
                password_request=result.signals.password_request,
                transfer_request=result.signals.transfer_request,
                remote_access_request=result.signals.remote_access_request,
                service_cancellation_threat=result.signals.service_cancellation_threat or flags["service_cancellation_threat"],
                subscription_fee_claim=result.signals.subscription_fee_claim or flags["subscription_fee_claim"],
                unverified_link_prompt=result.signals.unverified_link_prompt or flags["unverified_link_prompt"],
                sender_email=result.signals.sender_email or ocr_result.sender_email,
                suspicious_domain=result.signals.suspicious_domain or ocr_result.suspicious_domain_detected or ocr_result.visual_manipulation_suspected,
                special_offer_hook=result.signals.special_offer_hook or ocr_result.special_offer_detected,
                countdown_timer=result.signals.countdown_timer or ocr_result.countdown_timer_detected,
                requested_action=result.signals.requested_action or "update_payment_or_storage",
            )
            risk_assessment = self.risk_engine.evaluate(merged_signals)
            return self._act_on_risk_assessment(merged_signals, risk_assessment, sink)

        return result

