"""Clinical Safety Guardrails & Adversarial Prompt Injection Defense."""

import re
from typing import Any, Dict, List, Optional, Tuple


class ClinicalSafetyGuardrail:
    """Enterprise safety guardrail verifying prompt boundaries and neutralizing injection attempts."""

    INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions",
        r"system\s*override",
        r"debug\s+developer\s+mode",
        r"pretend\s+you\s+are",
        r"you\s+are\s+now\s+in\s+.*mode",
        r"reveal\s+(?:all\s+)?(?:system|confidential|cryptographic|secret)",
        r"administrator\s+privileges",
        r"output\s+all\s+(?:passwords|keys|dump)",
        r"disregard\s+safety",
        r"jailbreak",
    ]

    def __init__(self) -> None:
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.INJECTION_PATTERNS]

    def detect_prompt_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """Detect whether input contains adversarial jailbreaks or prompt injection attacks."""
        for pattern in self._compiled_patterns:
            match = pattern.search(text)
            if match:
                return True, match.group(0)
        return False, None

    def sanitize_untrusted_clinical_input(self, text: str) -> str:
        """Sanitize clinical text by neutralizing script tags and injection patterns."""
        sanitized = text
        # Remove HTML/script elements
        sanitized = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
        sanitized = re.sub(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)
        for pattern in self._compiled_patterns:
            sanitized = pattern.sub("[REDACTED_INSTRUCTION]", sanitized)
        return sanitized.strip()

    def verify_grounding(self, claim: str, context: str) -> bool:
        """Verify if a clinical claim is factually grounded in the provided context."""
        claim_clean = re.sub(r"[^\w\s]", "", claim.lower())
        words = [w for w in claim_clean.split() if len(w) > 3]
        if not words:
            return True
        context_lower = context.lower()
        matched = sum(1 for w in words if w in context_lower)
        return (matched / len(words)) >= 0.5
