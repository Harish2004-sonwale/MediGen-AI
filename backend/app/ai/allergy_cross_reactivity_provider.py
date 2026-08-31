"""Allergy Class Cross-Reactivity Evaluation Provider for Clinical Safety."""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("medigen.ai.allergy_cross_reactivity")

# Structural and pharmacologic cross-reactivity matrix
CROSS_REACTIVITY_MATRIX: Dict[str, Dict[str, Any]] = {
    "penicillin": {
        "class_name": "Beta-Lactam (Penicillins)",
        "cross_reactive_classes": [
            {
                "target_class": "Cephalosporins (1st/2nd Gen)",
                "risk_level": "MODERATE",
                "risk_pct": "2-5%",
                "mechanism": "Shared R1 side-chain and beta-lactam core structural homology.",
                "keywords": ["cefazolin", "cephalexin", "cefuroxime", "cefaclor"],
                "recommendation": "Use 3rd/4th gen cephalosporin (e.g. ceftriaxone, cefepime) or perform graded challenge if anaphylaxis history.",
            },
            {
                "target_class": "Cephalosporins (3rd/4th Gen)",
                "risk_level": "LOW_ADVISORY",
                "risk_pct": "<1%",
                "mechanism": "Distinct R1 side-chains significantly reduce cross-allergic antibody binding.",
                "keywords": ["ceftriaxone", "cefepime", "ceftazidime", "cefdinir"],
                "recommendation": "Generally safe unless prior reaction was severe cutaneous adverse reaction (SCAR/DRESS/TEN).",
            },
            {
                "target_class": "Carbapenems",
                "risk_level": "LOW_ADVISORY",
                "risk_pct": "<1%",
                "mechanism": "Minimal cross-reactivity demonstrated in clinical validation trials.",
                "keywords": ["meropenem", "ertapenem", "imipenem"],
                "recommendation": "Safe for administration under routine observation unless history of severe anaphylaxis.",
            },
            {
                "target_class": "Monobactams (Aztreonam)",
                "risk_level": "NONE",
                "risk_pct": "0%",
                "mechanism": "Aztreonam lacks cross-reactivity with penicillins (except ceftazidime due to shared side-chain).",
                "keywords": ["aztreonam"],
                "recommendation": "Safe alternative for penicillin-allergic patients.",
            },
        ],
        "keywords": ["penicillin", "amoxicillin", "ampicillin", "piperacillin", "augmentin", "zosyn", "unasyn", "oxacillin", "dicloxacillin"],
    },
    "cephalosporin": {
        "class_name": "Beta-Lactam (Cephalosporins)",
        "cross_reactive_classes": [
            {
                "target_class": "Penicillins",
                "risk_level": "MODERATE",
                "risk_pct": "2-5%",
                "mechanism": "Potential IgE cross-reactivity across beta-lactam rings.",
                "keywords": ["amoxicillin", "ampicillin", "piperacillin", "penicillin"],
                "recommendation": "Evaluate index reaction severity; consider non-beta-lactam alternative.",
            }
        ],
        "keywords": ["cefazolin", "cephalexin", "ceftriaxone", "cefepime", "ceftazidime", "cefuroxime", "cefdinir"],
    },
    "sulfonamide": {
        "class_name": "Sulfonamides (Antibiotics)",
        "cross_reactive_classes": [
            {
                "target_class": "Non-Antibiotic Sulfonamides (Diuretics/Celecoxib)",
                "risk_level": "LOW_ADVISORY",
                "risk_pct": "<0.5%",
                "mechanism": "Arylamine vs non-arylamine sulfonyl moiety structural difference; immunological cross-reactivity is extremely rare.",
                "keywords": ["furosemide", "hydrochlorothiazide", "bumetanide", "celecoxib", "glipizide"],
                "recommendation": "Non-antibiotic sulfonamides can generally be administered safely without pre-medication.",
            }
        ],
        "keywords": ["sulfamethoxazole", "bactrim", "septra", "tmp-smx", "sulfadiazine", "sulfasalazine"],
    },
    "nsaid": {
        "class_name": "Non-Steroidal Anti-Inflammatory Drugs (COX-1 Inhibitors)",
        "cross_reactive_classes": [
            {
                "target_class": "Other Non-Selective NSAIDs",
                "risk_level": "HIGH",
                "risk_pct": "80-95%",
                "mechanism": "Pharmacologic COX-1 inhibition shunting arachidonic acid to leukotriene synthesis (AERD).",
                "keywords": ["ibuprofen", "naproxen", "ketorolac", "indomethacin", "meloxicam", "aspirin", "toradol", "advil", "aleve"],
                "recommendation": "Strictly avoid non-selective NSAIDs. Consider selective COX-2 inhibitor (celecoxib) or acetaminophen with monitoring.",
            }
        ],
        "keywords": ["aspirin", "ibuprofen", "naproxen", "ketorolac", "toradol", "indomethacin", "meloxicam", "diclofenac"],
    },
    "opioid": {
        "class_name": "Opioids (Phenanthrenes)",
        "cross_reactive_classes": [
            {
                "target_class": "Phenylpiperidines (Fentanyl)",
                "risk_level": "LOW_ADVISORY",
                "risk_pct": "0%",
                "mechanism": "Distinct chemical class; fentanyl does not cross-react with phenanthrene true allergies.",
                "keywords": ["fentanyl", "sufentanil", "remifentanil"],
                "recommendation": "Fentanyl is a safe analgesic alternative for true phenanthrene morphine allergies.",
            }
        ],
        "keywords": ["morphine", "codeine", "hydrocodone", "oxycodone", "hydromorphone", "dilaudid", "oxymorphone"],
    },
}


class AllergyCrossReactivityProvider:
    """Evaluates drug orders against patient documented allergies for class-based cross-reactivity."""

    def evaluate_allergy_cross_reactivity(
        self,
        ordered_medication: str,
        patient_allergies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify potential cross-reactivity warnings for an ordered medication."""
        warnings: List[Dict[str, Any]] = []
        med_clean = ordered_medication.lower().strip()

        for allergy in patient_allergies:
            substance = str(allergy.get("substance", allergy.get("allergen", ""))).lower().strip()
            if not substance:
                continue

            # 1. Exact or direct match
            if substance in med_clean or med_clean in substance:
                warnings.append({
                    "warning_type": "DIRECT_ALLERGEN_MATCH",
                    "severity": "CRITICAL",
                    "ordered_medication": ordered_medication,
                    "documented_allergy": substance,
                    "risk_mechanism": "Direct allergen match with documented patient allergy.",
                    "clinical_recommendation": "DO NOT ADMINISTER. Select an alternative pharmacological class.",
                })
                continue

            # 2. Check cross-reactivity matrix
            for class_key, class_data in CROSS_REACTIVITY_MATRIX.items():
                # Check if patient allergy matches this class
                matches_allergy = any(kw in substance for kw in class_data["keywords"])
                if matches_allergy:
                    # Check if ordered med falls into any cross-reactive class
                    for cross_rel in class_data["cross_reactive_classes"]:
                        matches_ordered = any(kw in med_clean for kw in cross_rel["keywords"])
                        if matches_ordered:
                            warnings.append({
                                "warning_type": "CLASS_CROSS_REACTIVITY",
                                "severity": cross_rel["risk_level"],
                                "ordered_medication": ordered_medication,
                                "documented_allergy": substance,
                                "allergy_class": class_data["class_name"],
                                "target_class": cross_rel["target_class"],
                                "risk_percentage": cross_rel["risk_pct"],
                                "risk_mechanism": cross_rel["mechanism"],
                                "clinical_recommendation": cross_rel["recommendation"],
                            })

        return warnings


_allergy_provider: Optional[AllergyCrossReactivityProvider] = None


def get_allergy_cross_reactivity_provider() -> AllergyCrossReactivityProvider:
    global _allergy_provider
    if _allergy_provider is None:
        _allergy_provider = AllergyCrossReactivityProvider()
    return _allergy_provider
