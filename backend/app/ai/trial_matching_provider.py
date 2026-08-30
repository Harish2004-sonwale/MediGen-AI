"""Deterministic clinical trial matching and precision oncology decision support provider.

Phase 9.0.16: Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Optional


class BaseTrialMatchingProvider(ABC):
    """Abstract base provider for clinical trial matching and precision oncology."""

    @abstractmethod
    def evaluate_criterion(self, criterion: dict[str, Any], patient_context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single trial eligibility criterion against patient clinical data."""
        pass

    @abstractmethod
    def evaluate_trial_match(
        self, trial: dict[str, Any], criteria: list[dict[str, Any]], patient_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate overall patient match for a clinical trial."""
        pass

    @abstractmethod
    def evaluate_precision_treatment_eligibility(
        self, patient_context: dict[str, Any], biomarkers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Evaluate biomarker-driven targeted therapy eligibility."""
        pass


class MockTrialMatchingProvider(BaseTrialMatchingProvider):
    """Deterministic, 100% offline rule-based precision oncology and trial matching engine."""

    VERSION = "2026.1.0"

    # Pre-configured deterministic Precision Oncology Knowledge Base
    PRECISION_GUIDELINES: list[dict[str, Any]] = [
        {
            "gene_symbol": "EGFR",
            "variant_name": "L858R",
            "recommended_intervention": "Osimertinib (Tagrisso) 80mg Daily",
            "drug_class": "3rd-Generation EGFR Tyrosine Kinase Inhibitor",
            "indication": "EGFR L858R Metastatic Non-Small Cell Lung Cancer (NSCLC)",
            "evidence_source": "NCCN NSCLC Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": ["C797S", "MET_amplification"],
        },
        {
            "gene_symbol": "EGFR",
            "variant_name": "Exon 19 Deletion",
            "recommended_intervention": "Osimertinib (Tagrisso) 80mg Daily",
            "drug_class": "3rd-Generation EGFR Tyrosine Kinase Inhibitor",
            "indication": "EGFR Exon 19 Del Metastatic Non-Small Cell Lung Cancer (NSCLC)",
            "evidence_source": "NCCN NSCLC Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": ["C797S", "MET_amplification"],
        },
        {
            "gene_symbol": "EGFR",
            "variant_name": "T790M",
            "recommended_intervention": "Osimertinib (Tagrisso) 80mg Daily",
            "drug_class": "3rd-Generation EGFR Tyrosine Kinase Inhibitor",
            "indication": "EGFR T790M Acquired Resistance NSCLC",
            "evidence_source": "FDA Approved / Level 1A",
            "resistance_variants": ["C797S"],
        },
        {
            "gene_symbol": "ALK",
            "variant_name": "EML4-ALK Fusion",
            "recommended_intervention": "Alectinib (Alecensa) 600mg BID",
            "drug_class": "2nd-Generation ALK Tyrosine Kinase Inhibitor",
            "indication": "ALK-Positive Advanced/Metastatic NSCLC",
            "evidence_source": "NCCN NSCLC Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": ["G1202R"],
        },
        {
            "gene_symbol": "KRAS",
            "variant_name": "G12C",
            "recommended_intervention": "Sotorasib (Lumakras) 960mg Daily",
            "drug_class": "KRAS G12C Small Molecule Inhibitor",
            "indication": "KRAS G12C-Mutated Locally Advanced or Metastatic NSCLC",
            "evidence_source": "FDA Accelerated Approval / Level 1B",
            "resistance_variants": ["Y96D", "A59T"],
        },
        {
            "gene_symbol": "BRAF",
            "variant_name": "V600E",
            "recommended_intervention": "Dabrafenib (150mg BID) + Trametinib (2mg Daily)",
            "drug_class": "BRAF / MEK Dual Kinase Inhibitor Combination",
            "indication": "BRAF V600E Metastatic Melanoma / NSCLC / Solid Tumors",
            "evidence_source": "NCCN Biomarker Compendium / FDA Approved / Level 1A",
            "resistance_variants": [],
        },
        {
            "gene_symbol": "HER2",
            "variant_name": "Amplification",
            "recommended_intervention": "Trastuzumab Deruxtecan (Enhertu) 5.4 mg/kg IV q3w",
            "drug_class": "HER2-Directed Antibody-Drug Conjugate (ADC)",
            "indication": "HER2-Positive / HER2-Low Metastatic Breast & Gastric Cancer",
            "evidence_source": "NCCN Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": [],
        },
        {
            "gene_symbol": "BRCA1",
            "variant_name": "Pathogenic Mutation",
            "recommended_intervention": "Olaparib (Lynparza) 300mg BID",
            "drug_class": "Poly (ADP-ribose) Polymerase (PARP) Inhibitor",
            "indication": "gBRCAm / sBRCAm Metastatic Ovarian, Breast, Pancreatic & Prostate Cancer",
            "evidence_source": "NCCN Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": ["BRCA1_reversion_mutation"],
        },
        {
            "gene_symbol": "BRCA2",
            "variant_name": "Pathogenic Mutation",
            "recommended_intervention": "Olaparib (Lynparza) 300mg BID",
            "drug_class": "Poly (ADP-ribose) Polymerase (PARP) Inhibitor",
            "indication": "gBRCAm / sBRCAm Metastatic Ovarian, Breast, Pancreatic & Prostate Cancer",
            "evidence_source": "NCCN Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": ["BRCA2_reversion_mutation"],
        },
        {
            "gene_symbol": "PD-L1",
            "variant_name": "TPS >= 50%",
            "recommended_intervention": "Pembrolizumab (Keytruda) 200mg IV q3w Monotherapy",
            "drug_class": "Anti-PD-1 Immune Checkpoint Inhibitor",
            "indication": "First-Line Advanced NSCLC with High PD-L1 Expression (TPS >= 50%)",
            "evidence_source": "NCCN NSCLC Guidelines v2026.1 / Level 1A",
            "resistance_variants": [],
        },
        {
            "gene_symbol": "PD-L1",
            "variant_name": "TPS 1-49%",
            "recommended_intervention": "Pembrolizumab + Platinum-Doublet Chemotherapy",
            "drug_class": "Immune Checkpoint Inhibitor + Cytotoxic Chemotherapy",
            "indication": "First-Line Advanced NSCLC with Low/Moderate PD-L1 Expression (TPS 1-49%)",
            "evidence_source": "NCCN NSCLC Guidelines v2026.1 / Level 1A",
            "resistance_variants": [],
        },
        {
            "gene_symbol": "ROS1",
            "variant_name": "Fusion",
            "recommended_intervention": "Entrectinib (Rozlytrek) 600mg Daily",
            "drug_class": "ROS1 / TRK Tyrosine Kinase Inhibitor",
            "indication": "ROS1-Positive Metastatic NSCLC",
            "evidence_source": "NCCN Guidelines v2026.1 / FDA Approved / Level 1A",
            "resistance_variants": ["G2032R"],
        },
    ]

    def _compute_provenance_hash(self, payload: Any) -> str:
        """Generate deterministic SHA-256 hash for auditability."""
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def evaluate_criterion(self, criterion: dict[str, Any], patient_context: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single criterion against patient context."""
        c_type = criterion.get("criterion_type", "inclusion").lower()
        category = criterion.get("category", "").lower()
        field_name = criterion.get("field_name", "").lower()
        operator = criterion.get("operator", "==")
        expected_str = criterion.get("expected_value_str")
        expected_num = criterion.get("expected_value_num")
        expected_json = criterion.get("expected_value_json")
        desc = criterion.get("description", "")

        status = "UNKNOWN"
        evidence = "No patient data found for evaluation"
        reason = ""

        # 1. AGE Category
        if category == "age" or field_name == "age":
            pat_age = patient_context.get("age")
            if pat_age is None:
                status = "UNKNOWN"
                reason = "Patient age is missing from demographics record"
            else:
                passed = self._eval_operator(pat_age, operator, expected_num or expected_str)
                evidence = f"Patient age: {pat_age} years"
                if passed:
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"Age {pat_age} satisfies requirement ({operator} {expected_num or expected_str})"
                else:
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"Age {pat_age} does not meet requirement ({operator} {expected_num or expected_str})"

        # 2. GENDER / SEX Category
        elif category == "sex" or field_name in ("sex", "gender"):
            pat_gender = str(patient_context.get("gender", "")).lower()
            if not pat_gender:
                status = "UNKNOWN"
                reason = "Patient gender is missing"
            else:
                exp_g = str(expected_str or "").lower()
                passed = (exp_g in ("all", "both")) or (pat_gender == exp_g)
                evidence = f"Patient gender: {pat_gender}"
                if passed:
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"Gender matches criteria ({exp_g})"
                else:
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"Gender {pat_gender} does not match required {exp_g}"

        # 3. DIAGNOSIS Category
        elif category == "diagnosis" or field_name in ("diagnosis", "condition", "disease_condition"):
            diagnoses = [d.lower() for d in patient_context.get("diagnoses", [])]
            exp_d = str(expected_str or "").lower()
            if not diagnoses:
                status = "UNKNOWN"
                reason = "No confirmed clinical diagnoses recorded for patient"
            else:
                # Check for substring match or set containment
                matched_d = [d for d in diagnoses if exp_d in d or d in exp_d]
                if matched_d:
                    evidence = f"Patient confirmed diagnosis: {', '.join(matched_d)}"
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"Condition matches expected {expected_str}"
                else:
                    evidence = f"Patient active diagnoses: {', '.join(diagnoses)}"
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"Patient diagnoses do not include required {expected_str}"

        # 4. DISEASE STAGE Category
        elif category == "disease_stage" or field_name in ("stage", "disease_stage", "cancer_stage"):
            pat_stage = str(patient_context.get("cancer_stage", "")).upper()
            exp_s = str(expected_str or "").upper()
            if not pat_stage:
                status = "UNKNOWN"
                reason = "Cancer stage is unrecorded in clinical encounter"
            else:
                passed = self._eval_stage_match(pat_stage, operator, exp_s, expected_json)
                evidence = f"Documented disease stage: {pat_stage}"
                if passed:
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"Stage {pat_stage} matches required {exp_s}"
                else:
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"Stage {pat_stage} does not satisfy {operator} {exp_s}"

        # 5. BIOMARKER Category
        elif category == "biomarker" or field_name in ("gene_symbol", "variant_name", "biomarker"):
            biomarkers = patient_context.get("biomarkers", [])
            target_gene = str(criterion.get("expected_value_str") or criterion.get("field_name") or "").upper()
            target_var = str(criterion.get("expected_value_json") or "").upper()

            if not biomarkers:
                status = "UNKNOWN"
                reason = "No genomic sequencing panel or biomarker observations found"
            else:
                # Find matching biomarker
                found_gene_bm = [
                    bm for bm in biomarkers if bm.get("gene_symbol", "").upper() == target_gene or target_gene in bm.get("gene_symbol", "").upper()
                ]

                if operator in ("PRESENT", "=="):
                    if found_gene_bm:
                        # If specific variant is required
                        if target_var:
                            var_matches = [
                                bm for bm in found_gene_bm if target_var in bm.get("variant_name", "").upper()
                            ]
                            if var_matches:
                                evidence = f"Detected {var_matches[0].get('gene_symbol')} {var_matches[0].get('variant_name')}"
                                status = "PASS" if c_type == "inclusion" else "FAIL"
                                reason = f"Biomarker mutation confirmed: {evidence}"
                            else:
                                evidence = f"Gene mutated ({found_gene_bm[0].get('variant_name')}) but variant {target_var} not detected"
                                status = "FAIL" if c_type == "inclusion" else "PASS"
                                reason = f"Specific required variant {target_var} was not found"
                        else:
                            evidence = f"Detected {found_gene_bm[0].get('gene_symbol')} {found_gene_bm[0].get('variant_name')}"
                            status = "PASS" if c_type == "inclusion" else "FAIL"
                            reason = f"Biomarker confirmed: {evidence}"
                    else:
                        evidence = f"Biomarker {target_gene} was not detected in genomic panel"
                        status = "FAIL" if c_type == "inclusion" else "PASS"
                        reason = f"Required alteration {target_gene} absent"

                elif operator == "ABSENT" or c_type == "exclusion":
                    var_matches = []
                    if target_var:
                        var_matches = [
                            bm for bm in found_gene_bm if target_var in bm.get("variant_name", "").upper()
                        ]
                    else:
                        var_matches = found_gene_bm

                    if var_matches:
                        evidence = f"Detected prohibited biomarker alteration {var_matches[0].get('gene_symbol')} {var_matches[0].get('variant_name')}"
                        status = "FAIL"
                        reason = f"Prohibited alteration detected: {evidence}"
                    else:
                        evidence = f"Prohibited alteration {target_gene} {target_var} confirmed absent".strip()
                        status = "PASS"
                        reason = "Prohibited alteration confirmed absent"


                elif operator in (">=", ">", "<=", "<"):
                    # Numeric biomarker expression (e.g. PD-L1 TPS %, TMB mut/Mb)
                    matching_numeric_bm = [
                        bm for bm in found_gene_bm if bm.get("numeric_expression_value") is not None
                    ]
                    if matching_numeric_bm:
                        val = matching_numeric_bm[0]["numeric_expression_value"]
                        passed = self._eval_operator(val, operator, expected_num)
                        evidence = f"Measured {target_gene} expression: {val} {matching_numeric_bm[0].get('expression_unit', '%')}"
                        if passed:
                            status = "PASS" if c_type == "inclusion" else "FAIL"
                            reason = f"Numeric value {val} satisfies threshold ({operator} {expected_num})"
                        else:
                            status = "FAIL" if c_type == "inclusion" else "PASS"
                            reason = f"Numeric value {val} does not satisfy threshold ({operator} {expected_num})"
                    else:
                        status = "UNKNOWN"
                        reason = f"Numeric expression quantification missing for biomarker {target_gene}"

        # 6. PERFORMANCE STATUS (ECOG / Karnofsky)
        elif category == "performance_status" or field_name in ("ecog", "ecog_score", "performance_status"):
            ecog = patient_context.get("ecog_score")
            if ecog is None:
                status = "UNKNOWN"
                reason = "ECOG performance status is not documented in chart"
            else:
                passed = self._eval_operator(ecog, operator, expected_num or expected_str)
                evidence = f"Patient ECOG performance status: {ecog}"
                if passed:
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"ECOG score {ecog} meets criteria ({operator} {expected_num or expected_str})"
                else:
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"ECOG score {ecog} fails criteria ({operator} {expected_num or expected_str})"

        # 7. PRIOR THERAPY / MEDICATION
        elif category == "prior_therapy" or field_name in ("prior_therapy", "prior_medication", "medication"):
            prior_rx = [m.lower() for m in patient_context.get("prior_therapies", [])]
            target_rx = str(expected_str or "").lower()
            if not prior_rx:
                if c_type == "exclusion":
                    status = "PASS"
                    evidence = "No prior excluded therapies on record"
                    reason = "Patient has no documented prior therapy exposure"
                else:
                    status = "UNKNOWN"
                    reason = "No prior medication / systemic therapy history found"
            else:
                matched_rx = [m for m in prior_rx if target_rx in m or m in target_rx]
                if matched_rx:
                    evidence = f"Documented prior therapy: {', '.join(matched_rx)}"
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"Prior treatment history contains {target_rx}"
                else:
                    evidence = f"Prior therapies on file: {', '.join(prior_rx)}"
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"Required prior therapy {target_rx} was not found"

        # 8. LABORATORY VALUE / ORGAN FUNCTION
        elif category in ("laboratory_value", "organ_function"):
            labs = patient_context.get("lab_results", {})
            lab_key = field_name.lower().replace(" ", "_")
            if lab_key in labs:
                val = labs[lab_key]
                passed = self._eval_operator(val, operator, expected_num)
                evidence = f"Recent lab {field_name}: {val} {criterion.get('unit_of_measure', '')}"
                if passed:
                    status = "PASS" if c_type == "inclusion" else "FAIL"
                    reason = f"Lab value {val} satisfies threshold ({operator} {expected_num})"
                else:
                    status = "FAIL" if c_type == "inclusion" else "PASS"
                    reason = f"Lab value {val} out of bounds ({operator} {expected_num})"
            else:
                status = "UNKNOWN"
                reason = f"Recent laboratory quantification missing for {field_name}"

        # Default fallback
        else:
            status = "UNKNOWN"
            reason = f"Criterion '{field_name}' requires manual clinician verification"

        return {
            "criterion_id": criterion.get("criterion_id", f"CRIT-{field_name}"),
            "category": category,
            "criterion_type": c_type,
            "field_name": field_name,
            "description": desc or f"{category.upper()}: {field_name} {operator} {expected_str or expected_num}",
            "status": status,
            "evidence": evidence,
            "reason": reason,
        }

    def _eval_operator(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate comparison operator deterministically."""
        try:
            act_num = float(actual)
            exp_num = float(expected)
            if operator == "==":
                return act_num == exp_num
            elif operator == "!=":
                return act_num != exp_num
            elif operator == ">=":
                return act_num >= exp_num
            elif operator == ">":
                return act_num > exp_num
            elif operator == "<=":
                return act_num <= exp_num
            elif operator == "<":
                return act_num < exp_num
        except (ValueError, TypeError):
            pass

        act_s = str(actual).strip().lower()
        exp_s = str(expected).strip().lower()
        if operator == "==":
            return act_s == exp_s
        elif operator == "!=":
            return act_s != exp_s
        elif operator == "IN":
            if isinstance(expected, list):
                return act_s in [str(x).strip().lower() for x in expected]
            return act_s in exp_s
        elif operator == "NOT_IN":
            if isinstance(expected, list):
                return act_s not in [str(x).strip().lower() for x in expected]
            return act_s not in exp_s
        return False

    def _eval_stage_match(self, actual_stage: str, operator: str, expected_stage: str, expected_json: Any) -> bool:
        """Evaluate cancer disease stage hierarchy (I, II, III, IV, IIIB, IIIC, IVA, IVB)."""
        stage_rank = {
            "STAGE 0": 0, "0": 0,
            "STAGE I": 1, "STAGE IA": 1, "STAGE IB": 1, "I": 1, "IA": 1, "IB": 1,
            "STAGE II": 2, "STAGE IIA": 2, "STAGE IIB": 2, "II": 2, "IIA": 2, "IIB": 2,
            "STAGE III": 3, "STAGE IIIA": 3, "STAGE IIIB": 3, "STAGE IIIC": 3, "III": 3, "IIIA": 3, "IIIB": 3, "IIIC": 3,
            "STAGE IV": 4, "STAGE IVA": 4, "STAGE IVB": 4, "IV": 4, "IVA": 4, "IVB": 4,
            "ADVANCED": 4, "METASTATIC": 4, "RECURRENT": 4,
        }

        act_rank = stage_rank.get(actual_stage.upper(), -1)
        exp_rank = stage_rank.get(expected_stage.upper(), -1)

        if expected_json and isinstance(expected_json, list):
            valid_stages = [str(s).upper() for s in expected_json]
            return actual_stage.upper() in valid_stages or any(s in actual_stage.upper() for s in valid_stages)

        if act_rank >= 0 and exp_rank >= 0:
            if operator == "==":
                return act_rank == exp_rank
            elif operator == ">=":
                return act_rank >= exp_rank
            elif operator == "<=":
                return act_rank <= exp_rank
            elif operator == ">":
                return act_rank > exp_rank
            elif operator == "<":
                return act_rank < exp_rank

        return actual_stage.upper() in expected_stage.upper() or expected_stage.upper() in actual_stage.upper()

    def evaluate_trial_match(
        self, trial: dict[str, Any], criteria: list[dict[str, Any]], patient_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Evaluate complete trial eligibility and synthesize explainable decision-support result."""
        matched_criteria: list[dict[str, Any]] = []
        failed_criteria: list[dict[str, Any]] = []
        unknown_criteria: list[dict[str, Any]] = []

        # 1. Evaluate top-level trial attributes if explicit criteria list doesn't cover them
        eval_criteria = list(criteria)
        if not any(c.get("category") == "age" for c in eval_criteria):
            if trial.get("min_age_years") is not None:
                eval_criteria.append({
                    "criterion_id": "AUTO-AGE-MIN",
                    "category": "age",
                    "criterion_type": "inclusion",
                    "field_name": "age",
                    "operator": ">=",
                    "expected_value_num": trial["min_age_years"],
                    "description": f"Age >= {trial['min_age_years']} years",
                })
            if trial.get("max_age_years") is not None:
                eval_criteria.append({
                    "criterion_id": "AUTO-AGE-MAX",
                    "category": "age",
                    "criterion_type": "inclusion",
                    "field_name": "age",
                    "operator": "<=",
                    "expected_value_num": trial["max_age_years"],
                    "description": f"Age <= {trial['max_age_years']} years",
                })

        if not any(c.get("category") == "diagnosis" for c in eval_criteria):
            if trial.get("disease_condition"):
                eval_criteria.append({
                    "criterion_id": "AUTO-DIAG-MAIN",
                    "category": "diagnosis",
                    "criterion_type": "inclusion",
                    "field_name": "diagnosis",
                    "operator": "==",
                    "expected_value_str": trial["disease_condition"],
                    "description": f"Primary Condition: {trial['disease_condition']}",
                })

        # 2. Evaluate all criteria
        for crit in eval_criteria:
            res = self.evaluate_criterion(crit, patient_context)
            if res["status"] == "PASS":
                matched_criteria.append(res)
            elif res["status"] == "FAIL":
                failed_criteria.append(res)
            else:
                unknown_criteria.append(res)

        total_crit = len(eval_criteria)
        passed_count = len(matched_criteria)
        failed_count = len(failed_criteria)
        unknown_count = len(unknown_criteria)

        # 3. Determine Overall Match Status
        if failed_count > 0:
            match_status = "INELIGIBLE"
            match_score = 0.0
            explanation = (
                f"Patient is INELIGIBLE for {trial.get('title', 'trial')}. "
                f"Failed {failed_count} criteria: "
                + "; ".join([f"{f['description']} ({f['reason']})" for f in failed_criteria[:3]])
            )
        elif unknown_count == total_crit or (total_crit > 0 and passed_count == 0):
            match_status = "INSUFFICIENT_DATA"
            match_score = 10.0
            explanation = (
                f"INSUFFICIENT DATA to evaluate eligibility for {trial.get('title', 'trial')}. "
                f"All {unknown_count} criteria require further clinical laboratory or genomic sequencing data."
            )
        elif unknown_count > 0:
            match_status = "POTENTIAL_MATCH"
            match_score = round((passed_count / total_crit) * 100.0, 1)
            explanation = (
                f"Patient is a POTENTIAL MATCH ({match_score}%) for {trial.get('title', 'trial')}. "
                f"Satisfied {passed_count} criteria. {unknown_count} criteria require manual clinician review: "
                + "; ".join([f"{u['description']} ({u['reason']})" for u in unknown_criteria[:2]])
            )
        else:
            match_status = "MATCHED"
            match_score = 100.0
            explanation = (
                f"Patient is FULLY MATCHED (100%) for {trial.get('title', 'trial')}. "
                f"All {passed_count} inclusion criteria satisfied and zero exclusion criteria triggered."
            )

        provenance_payload = {
            "trial_id": trial.get("trial_id"),
            "patient_context": {
                "age": patient_context.get("age"),
                "gender": patient_context.get("gender"),
                "diagnoses": sorted(patient_context.get("diagnoses", [])),
                "cancer_stage": patient_context.get("cancer_stage"),
                "biomarker_keys": sorted([
                    f"{b.get('gene_symbol')}_{b.get('variant_name')}"
                    for b in patient_context.get("biomarkers", [])
                ]),
            },
            "match_status": match_status,
            "match_score": match_score,
            "algorithm_version": self.VERSION,
        }

        provenance_hash = self._compute_provenance_hash(provenance_payload)

        return {
            "match_status": match_status,
            "match_score": match_score,
            "matched_criteria": matched_criteria,
            "failed_criteria": failed_criteria,
            "unknown_criteria": unknown_criteria,
            "overall_explanation": explanation,
            "provenance_hash": provenance_hash,
            "algorithm_version": self.VERSION,
        }

    def evaluate_precision_treatment_eligibility(
        self, patient_context: dict[str, Any], biomarkers: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Synthesize precision oncology biomarker-driven treatment eligibility."""
        results: list[dict[str, Any]] = []
        detected_variants = {
            (b.get("gene_symbol", "").upper(), b.get("variant_name", "").upper()): b
            for b in biomarkers
        }
        detected_genes = {b.get("gene_symbol", "").upper(): b for b in biomarkers}

        for guideline in self.PRECISION_GUIDELINES:
            gene = guideline["gene_symbol"].upper()
            target_var = guideline["variant_name"].upper()
            intervention = guideline["recommended_intervention"]
            drug_class = guideline["drug_class"]
            indication = guideline["indication"]
            evidence = guideline["evidence_source"]
            resistances = [r.upper() for r in guideline.get("resistance_variants", [])]

            supporting_obs: list[str] = []
            contraindicating_obs: list[str] = []
            unknown_factors: list[str] = []
            eligibility_status = "NOT_ELIGIBLE"

            # 1. Check if gene / variant is detected
            matched_bm = None
            if (gene, target_var) in detected_variants:
                matched_bm = detected_variants[(gene, target_var)]
            elif gene == "PD-L1":
                # Special numeric threshold handling for PD-L1 TPS
                pd_bm = detected_genes.get("PD-L1")
                if pd_bm and pd_bm.get("numeric_expression_value") is not None:
                    tps = pd_bm["numeric_expression_value"]
                    if ">= 50%" in target_var and tps >= 50.0:
                        matched_bm = pd_bm
                    elif "1-49%" in target_var and 1.0 <= tps < 50.0:
                        matched_bm = pd_bm
            elif gene in ("BRCA1", "BRCA2") and "PATHOGENIC" in target_var:
                brca_bm = detected_genes.get(gene)
                if brca_bm and "pathogenic" in brca_bm.get("pathogenicity", "").lower():
                    matched_bm = brca_bm
            elif gene in detected_genes and target_var in detected_genes[gene].get("variant_name", "").upper():
                matched_bm = detected_genes[gene]

            if matched_bm:
                supporting_obs.append(
                    f"Biomarker confirmed: {matched_bm.get('gene_symbol')} {matched_bm.get('variant_name')} "
                    f"(Pathogenicity: {matched_bm.get('pathogenicity', 'N/A')}, Evidence: {matched_bm.get('evidence_level', 'N/A')})"
                )

                # 2. Check for known resistance mutations or contraindications
                for r_var in resistances:
                    if any(r_var in b.get("variant_name", "").upper() for b in biomarkers):
                        contraindicating_obs.append(
                            f"Acquired resistance variant detected: {r_var} (Blocks standard sensitivity)"
                        )

                # Check patient organ function
                labs = patient_context.get("lab_results", {})
                if "bilirubin" in labs and labs["bilirubin"] > 2.5:
                    contraindicating_obs.append(f"Severe hepatic impairment: Total Bilirubin {labs['bilirubin']} mg/dL")

                # Check missing parameters
                if "creatinine" not in labs:
                    unknown_factors.append("Recent Serum Creatinine / eGFR lab quantification missing")
                if not patient_context.get("cancer_stage"):
                    unknown_factors.append("Disease clinical staging not documented")

                # Determine final eligibility status
                if contraindicating_obs:
                    eligibility_status = "NOT_ELIGIBLE"
                elif unknown_factors and len(unknown_factors) > 1:
                    eligibility_status = "MANUAL_REVIEW"
                else:
                    eligibility_status = "ELIGIBLE"

                provenance_payload = {
                    "gene_symbol": gene,
                    "variant_name": target_var,
                    "intervention": intervention,
                    "eligibility_status": eligibility_status,
                    "supporting_obs": supporting_obs,
                    "contraindicating_obs": contraindicating_obs,
                    "algorithm_version": self.VERSION,
                }

                results.append({
                    "gene_symbol": gene,
                    "variant_name": target_var,
                    "recommended_intervention": intervention,
                    "drug_class": drug_class,
                    "indication": indication,
                    "eligibility_status": eligibility_status,
                    "evidence_source": evidence,
                    "supporting_observations_json": supporting_obs,
                    "contraindicating_observations_json": contraindicating_obs,
                    "unknown_factors_json": unknown_factors,
                    "provenance_hash": self._compute_provenance_hash(provenance_payload),
                })

        return results
