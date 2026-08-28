# Clinical Decision Support (CDS) & Safety Layer Documentation

## 1. Overview
The Clinical Safety Layer provides decision support checks to help clinicians identify potential medication duplications, documented allergy conflicts, adverse drug-drug interactions (DDI), and condition-drug contraindications.

> [!IMPORTANT]
> The safety engine is a **clinical decision support tool**, NOT an autonomous prescribing or diagnostic agent.
> All alerts require clinician review and never replace professional medical judgment.

---

## 2. Safety Check Architecture

```
                                Patient Records & Candidate Inputs
                                                |
                                                v
                    +-------------------------------------------------------+
                    |              Clinical Safety Service                  |
                    +-------------------------------------------------------+
                                                |
          +-------------------+-----------------+-------------------+
          |                   |                 |                   |
          v                   v                 v                   v
+-------------------+ +---------------+ +---------------+ +-------------------+
|  Medication       | | Allergy       | | Drug-Drug     | | Condition         |
|  Duplication      | | Warning       | | Interaction   | | Contraindication  |
|  Engine           | | Engine        | | (Pluggable)   | | (Pluggable)       |
+-------------------+ +---------------+ +---------------+ +-------------------+
          |                   |                 |                   |
          +-------------------+-----------------+-------------------+
                                                |
                                                v
                               +---------------------------------+
                               |     Clinical Safety Report      |
                               |  - Severity: CRITICAL to INFO   |
                               |  - requires_clinician_review: T |
                               |  - safe_to_proceed: Bool        |
                               |  - Verified Record Citations    |
                               +---------------------------------+
```

---

## 3. Severity Levels

| Severity | Definition | Action Required |
|---|---|---|
| `CRITICAL` | Severe life-threatening risk (e.g. anaphylactic allergy conflict, contraindicated nitrate + PDE5 inhibitor, ACE inhibitor in pregnancy) | Immediate clinician review; blocks automated clearance (`safe_to_proceed=False`) |
| `HIGH` | High risk of significant clinical toxicity or organ harm (e.g. Warfarin + Aspirin bleeding risk, Methotrexate + NSAID) | Urgent clinician review; blocks automated clearance (`safe_to_proceed=False`) |
| `MODERATE` | Potential interaction or duplicate therapy requiring monitoring (e.g. duplicate Metformin prescriptions, ACE inhibitor + Spironolactone hyperkalemia risk) | Clinician review recommended; monitoring advised |
| `LOW` / `INFO` | Minor clinical considerations or guidance information | Informational |

---

## 4. Pluggable Knowledge Boundary

External drug interaction databases (such as RxNorm, First Databank, or DrugBank) are decoupled behind standard abstract interfaces:
- `BaseDrugInteractionProvider`
- `BaseContraindicationProvider`

A deterministic `MockDrugInteractionProvider` and `MockContraindicationProvider` are included for local development and offline unit test execution without requiring cloud credentials or paid medical APIs.

---

## 5. API Endpoint

`POST /api/v1/patients/{patient_id}/safety/check`

#### Request Body (Optional):
```json
{
  "candidate_medications": ["Aspirin 81mg daily"],
  "active_conditions": ["Chronic atrial fibrillation"]
}
```

#### Response Example:
```json
{
  "patient_id": "PAT-20260828-A1B2",
  "alerts": [
    {
      "alert_id": "ALT-20260828-E4F5G6H7",
      "patient_id": "PAT-20260828-A1B2",
      "alert_type": "drug_interaction",
      "severity": "HIGH",
      "title": "Increased Bleeding Risk (Anticoagulant + Antiplatelet)",
      "explanation": "Concurrent use of Warfarin and Aspirin significantly elevates the risk of severe gastrointestinal and systemic hemorrhage. Clinician review and INR monitoring required.",
      "medications": ["Warfarin", "Aspirin"],
      "source_references": ["ACC/AHA Antithrombotic Guidelines"],
      "requires_clinician_review": true,
      "citations": [
        {
          "document_id": "DOCU-20260828-A1",
          "title": "Cardiology Discharge Note",
          "chunk_id": "CHK-20260828-001",
          "document_type": "clinical_note"
        }
      ]
    }
  ],
  "checked_items": 4,
  "safe_to_proceed": false,
  "summary": "Evaluated 4 clinical items: detected 1 clinical decision support alert(s) (0 critical, 1 high severity). Clinician review required.",
  "disclaimer": "Decision-support alert only. Clinician review required. Does not replace professional medical judgment.",
  "generated_at": "2026-08-28T14:45:00Z"
}
```
