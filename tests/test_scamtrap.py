"""Test suite for ScamTrap Counter-Deception Honey-Agent."""

import sys
import unittest
from pathlib import Path

# Ensure backend package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from guardian.scamtrap import ScamTrapIntelligenceSchema, run_scamtrap_agent


class TestScamTrap(unittest.TestCase):
    """Test suite for ScamTrap agent schema and execution."""

    def test_scamtrap_intelligence_schema_validation(self) -> None:
        """Verify ScamTrapIntelligenceSchema validates threat intelligence fields."""
        data = {
            "stalling_response": "Espere un momento, estoy buscando las gafas...",
            "extracted_phishing_urls": ["http://banco-fake-verify.com"],
            "extracted_ibans": ["ES9121000418450200051234"],
            "extracted_phone_numbers": ["+34600112233"],
            "scammer_tactics_summary": "Pretends to be bank tech support asking for urgent IBAN verification.",
        }
        schema = ScamTrapIntelligenceSchema(**data)
        self.assertTrue(schema.stalling_response.startswith("Espere"))
        self.assertIn("http://banco-fake-verify.com", schema.extracted_phishing_urls)
        self.assertIn("ES9121000418450200051234", schema.extracted_ibans)

    def test_run_scamtrap_agent_returns_valid_schema(self) -> None:
        """Verify run_scamtrap_agent extracts intelligence and returns valid schema."""
        sample_text = "Hola, le llamo del banco. Entre a http://seguridad-banco.fake y confirme su IBAN ES9121000418450200051234 ahora."
        intel = run_scamtrap_agent(sample_text)
        self.assertIsInstance(intel, ScamTrapIntelligenceSchema)
        self.assertTrue(len(intel.stalling_response) > 0)


if __name__ == "__main__":
    unittest.main()
