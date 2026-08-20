"""Structured scam taxonomy and domain knowledge base for Guardian Call.

Provides programmatic access to scam categories, attacker tactics, detection
heuristics, and prompt context helpers for Gemini LLM agents and Risk Engine.
"""

from typing import Any, Dict, List, Optional


SCAM_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "bank_otp_scam": {
        "id": "bank_otp_scam",
        "name_es": "Robo de OTP / Fraude Bancario",
        "name_en": "Bank OTP Interception Scam",
        "description": "Scammer poses as bank fraud department, creates panic over fraudulent transaction, requests 6-digit SMS OTP.",
        "identity_claim": "banco",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "otp_request"],
        "threat_level": "CRITICAL",
        "default_directive": "NO DIGA ESE CÓDIGO",
    },
    "tech_support_anydesk_scam": {
        "id": "tech_support_anydesk_scam",
        "name_es": "Falso Soporte Técnico y Acceso Remoto",
        "name_en": "Tech Support Remote Control Scam",
        "description": "Scammer claims victim's computer has a virus, demands installation of AnyDesk/TeamViewer.",
        "identity_claim": "soporte_tecnico",
        "critical_signals": ["identity_claim", "urgency", "remote_access_request"],
        "threat_level": "CRITICAL",
        "default_directive": "NO INSTALE NINGUNA APLICACIÓN",
    },
    "police_law_enforcement_scam": {
        "id": "police_law_enforcement_scam",
        "name_es": "Suplantación de Autoridad / Policía / Hacienda",
        "name_en": "Law Enforcement & Tax Impersonation Scam",
        "description": "Scammer poses as police or tax official threatening legal action or fine unless wire payment is made immediately.",
        "identity_claim": "policia",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "secrecy_request"],
        "threat_level": "HIGH",
        "default_directive": "CUELGUE Y VERIFIQUE CON LA POLICÍA",
    },
    "family_kidnapping_whatsapp_scam": {
        "id": "family_kidnapping_whatsapp_scam",
        "name_es": "Familiar en Apuros / Hijo con Teléfono Roto",
        "name_en": "Family Emergency / Kidnapping Scam",
        "description": "Scammer poses as child/relative in urgent distress (hospital/jail) needing immediate money.",
        "identity_claim": "familiar",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "transfer_request"],
        "threat_level": "CRITICAL",
        "default_directive": "LLAME A SU FAMILIAR DIRECTAMENTE",
    },
    "synthetic_ai_voice_family_scam": {
        "id": "synthetic_ai_voice_family_scam",
        "name_es": "Clonación de Voz con IA",
        "name_en": "Synthetic Voice AI Cloning Scam",
        "description": "Scammer uses AI voice cloning to impersonate a loved one or CEO for urgent money transfers.",
        "identity_claim": "familiar_ia",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "transfer_request"],
        "threat_level": "CRITICAL",
        "default_directive": "VERIFIQUE MEDIANTE PREGUNTA PERSONAL",
    },
    "crypto_investment_guaranteed_scam": {
        "id": "crypto_investment_guaranteed_scam",
        "name_es": "Inversiones Ficticias en Criptomonedas",
        "name_en": "Crypto & Forex Investment Trap",
        "description": "Scammer offers high guaranteed return on crypto/forex platform with zero risk.",
        "identity_claim": "broker",
        "critical_signals": ["identity_claim", "financial_context", "transfer_request"],
        "threat_level": "HIGH",
        "default_directive": "NO REALICE TRANSFERENCIAS DE INVERSIÓN",
    },
    "delivery_customs_fee_scam": {
        "id": "delivery_customs_fee_scam",
        "name_es": "Falsa Paquetería / Tasas de Aduana",
        "name_en": "Parcel Delivery Customs Fee Scam",
        "description": "Scammer alerts about undelivered parcel requiring small fee or credit card details via phone.",
        "identity_claim": "correos",
        "critical_signals": ["identity_claim", "financial_context", "requested_action"],
        "threat_level": "SUSPICIOUS",
        "default_directive": "NO FACILITE DATOS DE TARJETA",
    },
    "ceo_giftcard_wire_scam": {
        "id": "ceo_giftcard_wire_scam",
        "name_es": "Fraude del CEO / Tarjetas de Regalo",
        "name_en": "Executive Impersonation & Gift Card Scam",
        "description": "Scammer poses as CEO/executive asking employee for secret gift card purchases.",
        "identity_claim": "director_general",
        "critical_signals": ["identity_claim", "financial_context", "secrecy_request", "transfer_request"],
        "threat_level": "HIGH",
        "default_directive": "CONFIRME CON SU EMPRESA POR CANAL OFICIAL",
    },
    "refund_overpayment_scam": {
        "id": "refund_overpayment_scam",
        "name_es": "Falso Reembolso y Exceso de Pago",
        "name_en": "Fake Refund & Overpayment Scam",
        "description": "Scammer claims to refund money, pretends to overpay, and demands refund of difference.",
        "identity_claim": "servicio_cliente",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "remote_access_request"],
        "threat_level": "CRITICAL",
        "default_directive": "NO DEVUELVA DINERO SIN VERIFICAR SU BANCO",
    },
    "utility_contract_switch_scam": {
        "id": "utility_contract_switch_scam",
        "name_es": "Falso Inspector de Suministros (Luz/Gas)",
        "name_en": "Utility Contract Tariff Switch Scam",
        "description": "Scammer poses as power/gas company threatening price hike unless IBAN/OTP is provided.",
        "identity_claim": "compania_electrica",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "otp_request"],
        "threat_level": "HIGH",
        "default_directive": "NO PROPORCIONE SU IBAN O CÓDIGOS SMS",
    },
    "mfa_fatigue_it_helpdesk_scam": {
        "id": "mfa_fatigue_it_helpdesk_scam",
        "name_es": "Falso Soporte TI y Fatiga MFA (Scattered Spider)",
        "name_en": "IT Helpdesk MFA Push Bombing Scam",
        "description": "Scammer triggers continuous MFA push notifications and poses as IT helpdesk demanding prompt approval.",
        "identity_claim": "soporte_tecnico",
        "critical_signals": ["identity_claim", "urgency", "otp_request", "remote_access_request"],
        "threat_level": "CRITICAL",
        "default_directive": "NO APRUEBE NINGUNA NOTIFICACIÓN PUSH",
    },
    "bank_secure_vault_scam": {
        "id": "bank_secure_vault_scam",
        "name_es": "Falsa Bóveda Segura Bancaria",
        "name_en": "Fake Bank Secure Vault Scam",
        "description": "Scammer uses preemptive objection handling claiming to move funds into a safe vault account.",
        "identity_claim": "banco",
        "critical_signals": ["identity_claim", "financial_context", "urgency", "transfer_request"],
        "threat_level": "CRITICAL",
        "default_directive": "NO TRANSFERIR FONDOS A OTRA CUENTA",
    },
}


ATTACKER_TACTICS: List[Dict[str, str]] = [
    {
        "name": "Authority & Trust Hijacking",
        "description": "Caller claims to represent trusted institution (Bank, Police, Microsoft, Government).",
    },
    {
        "name": "Urgency & Panic Inductions",
        "description": "Imposes extreme artificial time limits (e.g. 5 minutes) to disable critical thinking.",
    },
    {
        "name": "Forced Isolation & Secrecy",
        "description": "Demands user not hang up, talk to family, or consult bank teller.",
    },
    {
        "name": "Credential & Key Extraction",
        "description": "Requests SMS OTP, passwords, PINs, or IBAN numbers.",
    },
    {
        "name": "Device Takeover",
        "description": "Coerces user to download remote management software (AnyDesk, TeamViewer).",
    },
]


def get_scam_category(category_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve details for a specific scam category."""
    return SCAM_TAXONOMY.get(category_id)


def get_all_scam_categories() -> List[Dict[str, Any]]:
    """Get list of all supported scam categories."""
    return list(SCAM_TAXONOMY.values())


def get_few_shot_examples() -> str:
    """Provide structured Few-Shot examples for prompt in-context learning."""
    return """
FEW-SHOT EXAMPLES FOR SIGNAL EXTRACTION:

Example 1 (Bank Fraud OTP Theft):
Input: "Hola, le llamamos del departamento de fraude del Banco Santander. Hay una transferencia sospecosa de 450 euros. Le envié un SMS de 6 dígitos, dígamelo ya para cancelarla y no cuelgue."
Output JSON:
{
  "identity_claim": "banco",
  "identity_verified": false,
  "financial_context": true,
  "urgency": true,
  "secrecy_request": true,
  "otp_request": true,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": "share_otp"
}

Example 2 (Tech Support AnyDesk):
Input: "Good afternoon, this is Microsoft technical support. Your computer has malware. Download AnyDesk right now so we can fix it."
Output JSON:
{
  "identity_claim": "soporte_tecnico",
  "identity_verified": false,
  "financial_context": false,
  "urgency": true,
  "secrecy_request": false,
  "otp_request": false,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": true,
  "requested_action": "install_remote_software"
}

Example 3 (Legitimate Bank Call - False Positive Suppression):
Input: "Hola María, le habla Carlos de su oficina bancaria. Recuerde que la semana que viene vence su plazo fijo. El banco nunca le pedirá sus claves por teléfono. Pase por la oficina si desea informarse."
Output JSON:
{
  "identity_claim": "banco",
  "identity_verified": false,
  "financial_context": true,
  "urgency": false,
  "secrecy_request": false,
  "otp_request": false,
  "password_request": false,
  "transfer_request": false,
  "remote_access_request": false,
  "requested_action": null
}
"""


def get_knowledge_prompt_context() -> str:
    """Generate concise domain knowledge context to enrich LLM prompts."""
    lines = ["Known Scam Taxonomy and Critical Signals:"]
    for cat in SCAM_TAXONOMY.values():
        lines.append(
            f"- [{cat['id']}] {cat['name_es']} (Claim: {cat['identity_claim']}): "
            f"Signals: {', '.join(cat['critical_signals'])}"
        )
    lines.append("\n" + get_few_shot_examples())
    return "\n".join(lines)

