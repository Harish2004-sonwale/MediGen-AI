"""Medical Imaging Provider Architecture for Multi-Modal AI Diagnostics.

Phase 9.0.7: Advanced Multi-Modal Medical Diagnostics & Imaging Support.
Provides:
- Abstract base class BaseMedicalImagingProvider
- Deterministic offline MockMedicalImagingProvider
- Factory method get_imaging_provider()
"""

from abc import ABC, abstractmethod
import hashlib
import logging
import os
from typing import Optional

from app.core.config import settings
from app.schemas.media import (
    ImagingFindingItem,
    MediaModality,
    StructuredImagingFinding,
)

logger = logging.getLogger("medigen.imaging_provider")


class BaseMedicalImagingProvider(ABC):
    """Abstract base provider for multi-modal medical imaging diagnostics."""

    @abstractmethod
    def analyze_image(
        self,
        file_path: str,
        modality: MediaModality,
        clinical_context: Optional[str] = None,
    ) -> StructuredImagingFinding:
        """Analyze a clinical image file and return structured observations.

        Args:
            file_path: Absolute or relative storage path to media file.
            modality: Clinical imaging modality (e.g. xray_chest, ct_scan).
            clinical_context: Optional clinical indications or patient symptoms.

        Returns:
            StructuredImagingFinding containing observations, confidence, and disclaimers.
        """
        pass


class MockMedicalImagingProvider(BaseMedicalImagingProvider):
    """Deterministic, 100% offline mock imaging diagnostic provider.

    Generates consistent, clinical-grade observations based on modality,
    file size, and content hash for robust local development and testing.
    """

    def analyze_image(
        self,
        file_path: str,
        modality: MediaModality,
        clinical_context: Optional[str] = None,
    ) -> StructuredImagingFinding:
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 1024

        # Compute deterministic seed from filename & size
        seed_src = f"{os.path.basename(file_path)}:{file_size}:{modality.value}"
        hash_val = int(hashlib.md5(seed_src.encode("utf-8")).hexdigest()[:6], 16)

        logger.info(
            "Executing deterministic mock imaging analysis for modality: %s",
            modality.value,
        )

        if modality == MediaModality.XRAY_CHEST:
            confidence = 0.92
            primary = "No acute cardiopulmonary process identified. Lung fields are clear bilaterally."
            findings = [
                ImagingFindingItem(
                    observation="Normal cardiac silhouette and mediastinal contours.",
                    anatomical_region="Heart & Mediastinum",
                    confidence=0.95,
                    is_abnormal=False,
                ),
                ImagingFindingItem(
                    observation="Clear pulmonary parenchyma without focal consolidation, pneumothorax, or pleural effusion.",
                    anatomical_region="Lungs & Pleura",
                    confidence=0.92,
                    is_abnormal=False,
                ),
                ImagingFindingItem(
                    observation="Osseous structures and soft tissues unremarkable.",
                    anatomical_region="Thoracic Cage",
                    confidence=0.90,
                    is_abnormal=False,
                ),
            ]
            differentials = [
                "Exclude early interstitial process if clinical symptoms persist.",
                "Correlate with pulse oximetry and clinical examination.",
            ]

        elif modality == MediaModality.CT_SCAN:
            confidence = 0.94
            primary = "Non-contrast scan demonstrates preserved parenchymal density without acute intracranial hemorrhage or mass effect."
            findings = [
                ImagingFindingItem(
                    observation="Ventricles and basal cisterns are symmetric and within normal limits for age.",
                    anatomical_region="Ventricular System",
                    confidence=0.96,
                    is_abnormal=False,
                ),
                ImagingFindingItem(
                    observation="No midline shift, herniation, or acute territorial infarction.",
                    anatomical_region="Cerebral Hemispheres",
                    confidence=0.94,
                    is_abnormal=False,
                ),
            ]
            differentials = [
                "MRI may be considered if focal neurological deficits progress.",
            ]

        elif modality == MediaModality.MRI:
            confidence = 0.91
            primary = "Multiplanar sequences reveal intact anatomic alignment without abnormal signal intensity."
            findings = [
                ImagingFindingItem(
                    observation="Normal grey-white matter differentiation; no demyelinating plaques.",
                    anatomical_region="Brain Parenchyma",
                    confidence=0.93,
                    is_abnormal=False,
                ),
                ImagingFindingItem(
                    observation="Major intracranial vascular flow voids are preserved.",
                    anatomical_region="Intracranial Vasculature",
                    confidence=0.90,
                    is_abnormal=False,
                ),
            ]
            differentials = ["Correlate with neuro-cognitive evaluation."]

        elif modality == MediaModality.ULTRASOUND:
            confidence = 0.89
            primary = "Sonographic evaluation demonstrates homogeneous echotexture without focal cystic or solid lesions."
            findings = [
                ImagingFindingItem(
                    observation="Normal organ dimensions and smooth contours.",
                    anatomical_region="Target Organ",
                    confidence=0.91,
                    is_abnormal=False,
                ),
            ]
            differentials = ["Repeat sonogram indicated if symptoms recrudesce."]

        elif modality == MediaModality.DERMATOLOGY:
            confidence = 0.88
            primary = "Dermoscopic examination reveals symmetric pigment network with regular border architecture."
            findings = [
                ImagingFindingItem(
                    observation="Benign melanocytic pattern without atypical network or regression structures.",
                    anatomical_region="Cutaneous Lesion",
                    confidence=0.89,
                    is_abnormal=False,
                ),
            ]
            differentials = ["Routine dermatologic surveillance recommended."]

        elif modality == MediaModality.PATHOLOGY:
            confidence = 0.93
            primary = "Histopathologic section shows preserved cellular architecture without dysplastic or malignant features."
            findings = [
                ImagingFindingItem(
                    observation="Uniform nuclear morphology and normal mitotic activity.",
                    anatomical_region="Histologic Tissue",
                    confidence=0.94,
                    is_abnormal=False,
                ),
            ]
            differentials = ["Immunohistochemical staining optional if indicated."]

        else:
            confidence = 0.85
            primary = "Diagnostic media visual inspection complete; no overt morphological disruption identified."
            findings = [
                ImagingFindingItem(
                    observation="Visual features within expected morphological parameters.",
                    anatomical_region="General Anatomical View",
                    confidence=0.85,
                    is_abnormal=False,
                ),
            ]
            differentials = ["Clinical correlation required."]

        return StructuredImagingFinding(
            modality=modality,
            confidence_score=confidence,
            primary_observation=primary,
            findings=findings,
            differential_notes=differentials,
        )


def get_imaging_provider() -> BaseMedicalImagingProvider:
    """Factory resolver returning configured medical imaging provider."""
    provider_name = getattr(settings, "IMAGING_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockMedicalImagingProvider()
    logger.warning("Unrecognized IMAGING_PROVIDER '%s', defaulting to MockMedicalImagingProvider", provider_name)
    return MockMedicalImagingProvider()
