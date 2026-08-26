import os
import pytest
import time
from dotenv import load_dotenv

load_dotenv()
os.environ["PYTEST_CURRENT_TEST"] = "1"
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

from backend.guardian.pipeline import GuardianPipeline
from backend.guardian.signals import text_keyword_flags


def test_temperature_benchmark_determinism():
    """Verify system stability and 100% determinism across test prompts."""
    pipeline = GuardianPipeline()
    test_prompts = [
        "ALERTA: Su cuenta bancaria BBVA ha sido bloqueada. Ingrese su código de 6 dígitos aquí.",
        "Your Account Has Been Blocked! Your Photos and Videos will be Removed. 50 GB bonus storage. Expires in 4 minutes.",
        "Hola mamá, he cambiado de número de teléfono. Necesito que me hagas una transferencia urgente de 400 euros.",
        "Hola, buenas tardes. Le llamamos de soporte técnico para verificar el estado de su ordenador.",
    ]

    for prompt in test_prompts:
        res1 = pipeline.process_text(prompt)
        res2 = pipeline.process_text(prompt)

        assert res1.risk_assessment.level == res2.risk_assessment.level
        assert res1.canary_decision.action == res2.canary_decision.action
        assert res1.canary_decision.allowed == res2.canary_decision.allowed
