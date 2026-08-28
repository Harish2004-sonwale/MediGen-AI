from abc import ABC, abstractmethod
from typing import Any, Optional
import re
from pydantic import BaseModel, Field

from app.schemas.fhir import FHIRResourceType


class FHIRValidationReport(BaseModel):
    is_valid: bool = Field(..., description="Whether validation succeeded without errors")
    resource_type: Optional[str] = Field(default=None, description="Identified resourceType")
    errors: list[str] = Field(default_factory=list, description="List of blocking validation errors")
    warnings: list[str] = Field(default_factory=list, description="List of non-blocking warnings")


class BaseFHIRValidator(ABC):
    """Abstract interface for FHIR R4 schema and structure validation."""

    @abstractmethod
    def validate_resource(self, resource_data: dict[str, Any]) -> FHIRValidationReport:
        """Validate a single FHIR R4 resource dictionary."""
        raise NotImplementedError

    @abstractmethod
    def validate_bundle(self, bundle_data: dict[str, Any]) -> FHIRValidationReport:
        """Validate a FHIR R4 Bundle dictionary and its entries."""
        raise NotImplementedError


class StandardFHIRValidator(BaseFHIRValidator):
    """Offline, deterministic FHIR R4 validator enforcing core structure and clinical references."""

    SUPPORTED_TYPES = {
        FHIRResourceType.PATIENT.value,
        FHIRResourceType.ENCOUNTER.value,
        FHIRResourceType.CONDITION.value,
        FHIRResourceType.MEDICATION_STATEMENT.value,
        FHIRResourceType.OBSERVATION.value,
        FHIRResourceType.BUNDLE.value,
    }

    REFERENCE_PATTERN = re.compile(r"^(?:[A-Za-z]+/[A-Za-z0-9\-_.]+|urn:uuid:[a-fA-F0-9\-]+)$")

    def validate_resource(self, resource_data: dict[str, Any]) -> FHIRValidationReport:
        """Validate a single FHIR resource dictionary."""
        errors: list[str] = []
        warnings: list[str] = []

        if not isinstance(resource_data, dict):
            return FHIRValidationReport(
                is_valid=False,
                resource_type=None,
                errors=["Resource payload must be a valid JSON object."],
            )

        resource_type = resource_data.get("resourceType")
        if not resource_type:
            return FHIRValidationReport(
                is_valid=False,
                resource_type=None,
                errors=["Missing mandatory 'resourceType' field."],
            )

        if resource_type not in self.SUPPORTED_TYPES:
            return FHIRValidationReport(
                is_valid=False,
                resource_type=str(resource_type),
                errors=[f"Unsupported FHIR resourceType: '{resource_type}'. Supported types: {sorted(list(self.SUPPORTED_TYPES))}"],
            )

        # Delegate to type-specific validators
        if resource_type == FHIRResourceType.PATIENT.value:
            self._validate_patient(resource_data, errors, warnings)
        elif resource_type == FHIRResourceType.ENCOUNTER.value:
            self._validate_encounter(resource_data, errors, warnings)
        elif resource_type == FHIRResourceType.CONDITION.value:
            self._validate_condition(resource_data, errors, warnings)
        elif resource_type == FHIRResourceType.MEDICATION_STATEMENT.value:
            self._validate_medication_statement(resource_data, errors, warnings)
        elif resource_type == FHIRResourceType.OBSERVATION.value:
            self._validate_observation(resource_data, errors, warnings)
        elif resource_type == FHIRResourceType.BUNDLE.value:
            return self.validate_bundle(resource_data)

        return FHIRValidationReport(
            is_valid=len(errors) == 0,
            resource_type=str(resource_type),
            errors=errors,
            warnings=warnings,
        )

    def validate_bundle(self, bundle_data: dict[str, Any]) -> FHIRValidationReport:
        """Validate a FHIR Bundle and its child entries."""
        errors: list[str] = []
        warnings: list[str] = []

        if not isinstance(bundle_data, dict):
            return FHIRValidationReport(is_valid=False, resource_type="Bundle", errors=["Bundle payload must be a JSON object."])

        if bundle_data.get("resourceType") != "Bundle":
            errors.append("Bundle resourceType must be 'Bundle'.")

        bundle_type = bundle_data.get("type")
        if not bundle_type:
            errors.append("Bundle must specify a 'type' (e.g. 'collection', 'batch', 'transaction').")

        entries = bundle_data.get("entry")
        if entries is not None:
            if not isinstance(entries, list):
                errors.append("Bundle 'entry' field must be a list.")
            else:
                for idx, entry in enumerate(entries):
                    if not isinstance(entry, dict):
                        errors.append(f"Bundle entry[{idx}] must be an object.")
                        continue
                    res = entry.get("resource")
                    if res:
                        sub_report = self.validate_resource(res)
                        if not sub_report.is_valid:
                            for err in sub_report.errors:
                                errors.append(f"Entry[{idx}] ({sub_report.resource_type or 'Unknown'}): {err}")
                    else:
                        warnings.append(f"Bundle entry[{idx}] contains no embedded 'resource'.")

        return FHIRValidationReport(
            is_valid=len(errors) == 0,
            resource_type="Bundle",
            errors=errors,
            warnings=warnings,
        )

    def _validate_patient(self, data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
        names = data.get("name")
        if names is not None and not isinstance(names, list):
            errors.append("Patient 'name' field must be a list of HumanName objects.")
        elif names and isinstance(names, list):
            has_valid_name = any(isinstance(n, dict) and (n.get("family") or n.get("given") or n.get("text")) for n in names)
            if not has_valid_name:
                warnings.append("Patient name list contains no family, given, or text name parts.")

        gender = data.get("gender")
        if gender is not None and str(gender).lower() not in {"male", "female", "other", "unknown"}:
            errors.append(f"Invalid FHIR administrative gender: '{gender}'. Must be male | female | other | unknown.")

        birth_date = data.get("birthDate")
        if birth_date and not re.match(r"^\d{4}(?:-\d{2}-\d{2})?$", str(birth_date)):
            errors.append("Patient 'birthDate' must follow ISO YYYY or YYYY-MM-DD format.")

    def _validate_encounter(self, data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
        status = data.get("status")
        if not status:
            errors.append("Encounter 'status' is required.")

        subject = data.get("subject")
        if not subject or not isinstance(subject, dict) or not subject.get("reference"):
            errors.append("Encounter 'subject.reference' (Patient link) is required.")
        else:
            self._validate_reference(subject.get("reference"), "subject", errors)

    def _validate_condition(self, data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
        subject = data.get("subject")
        if not subject or not isinstance(subject, dict) or not subject.get("reference"):
            errors.append("Condition 'subject.reference' is required.")
        else:
            self._validate_reference(subject.get("reference"), "subject", errors)

        code = data.get("code")
        note = data.get("note")
        if not code and not note:
            errors.append("Condition must provide at least a 'code' (CodeableConcept) or a 'note'.")

    def _validate_medication_statement(self, data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
        status = data.get("status")
        if not status:
            errors.append("MedicationStatement 'status' is required.")

        subject = data.get("subject")
        if not subject or not isinstance(subject, dict) or not subject.get("reference"):
            errors.append("MedicationStatement 'subject.reference' is required.")
        else:
            self._validate_reference(subject.get("reference"), "subject", errors)

        med_code = data.get("medicationCodeableConcept")
        note = data.get("note")
        if not med_code and not note:
            errors.append("MedicationStatement must specify 'medicationCodeableConcept' or 'note'.")

    def _validate_observation(self, data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
        status = data.get("status")
        if not status:
            errors.append("Observation 'status' is required.")

        code = data.get("code")
        if not code or not isinstance(code, dict):
            errors.append("Observation 'code' (CodeableConcept) is required.")

        subject = data.get("subject")
        if subject and isinstance(subject, dict) and subject.get("reference"):
            self._validate_reference(subject.get("reference"), "subject", errors)

    def _validate_reference(self, ref: Any, field_name: str, errors: list[str]) -> None:
        if not isinstance(ref, str) or not self.REFERENCE_PATTERN.match(ref.strip()):
            errors.append(f"Invalid reference format for '{field_name}': '{ref}'. Must be 'ResourceType/id' or 'urn:uuid:...'")


_validator_instance: Optional[StandardFHIRValidator] = None


def get_fhir_validator() -> BaseFHIRValidator:
    """Factory function for FHIR validator."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = StandardFHIRValidator()
    return _validator_instance
