"""
Agricultural and community report category definitions (PK-006/PK-007 prerequisite).

These categories are designed for future resident field-report intake.
They are NOT active yet — the operational intake workflow requires P1-002
(durable persistence), SEC-001 (security audit), and an authorized integration.

This module defines the category taxonomy only, without enabling submission.
"""
from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class ReportCategory(str, Enum):
    """Supported community report categories.

    Each category represents a distinct type of flood-related impact.
    Categories are designed to separate different types of information
    for appropriate routing, moderation, and verification.
    """

    CROP_DAMAGE = "crop_damage"
    LIVESTOCK_AFFECTED = "livestock_affected"
    FODDER_WATER_NEED = "fodder_water_need"
    IRRIGATION_DAMAGE = "irrigation_damage"
    ROAD_BRIDGE_INACCESSIBLE = "road_bridge_inaccessible"
    EQUIPMENT_DAMAGE = "equipment_damage"
    WATER_CONTAMINATION = "water_contamination"
    GENERAL_FLOOD_IMPACT = "general_flood_impact"


class CategoryMetadata(NamedTuple):
    """Display and routing metadata for a report category."""

    category: ReportCategory
    label_en: str
    description_en: str
    icon: str
    requires_location: bool
    sensitive_location: bool


CATEGORY_REGISTRY: tuple[CategoryMetadata, ...] = (
    CategoryMetadata(
        category=ReportCategory.CROP_DAMAGE,
        label_en="Crop damage",
        description_en=(
            "Standing crop, stored grain, seed stock, or planting material "
            "damaged or destroyed by flooding."
        ),
        icon="🌾",
        requires_location=False,
        sensitive_location=True,
    ),
    CategoryMetadata(
        category=ReportCategory.LIVESTOCK_AFFECTED,
        label_en="Lost or affected livestock",
        description_en=(
            "Animals lost, injured, displaced, or in immediate need of "
            "veterinary attention due to flooding."
        ),
        icon="🐄",
        requires_location=False,
        sensitive_location=True,
    ),
    CategoryMetadata(
        category=ReportCategory.FODDER_WATER_NEED,
        label_en="Fodder or clean water need",
        description_en=(
            "Animal fodder supply disrupted or clean drinking water for "
            "animals unavailable."
        ),
        icon="🌿",
        requires_location=False,
        sensitive_location=False,
    ),
    CategoryMetadata(
        category=ReportCategory.IRRIGATION_DAMAGE,
        label_en="Damaged irrigation channel or pump",
        description_en=(
            "Irrigation canal, pump, pipe or related infrastructure damaged "
            "or non-functional due to flooding."
        ),
        icon="💧",
        requires_location=False,
        sensitive_location=False,
    ),
    CategoryMetadata(
        category=ReportCategory.ROAD_BRIDGE_INACCESSIBLE,
        label_en="Inaccessible road or bridge",
        description_en=(
            "Road, bridge or access route blocked, damaged, or submerged. "
            "Distinguish from an official road closure."
        ),
        icon="🚧",
        requires_location=False,
        sensitive_location=False,
    ),
    CategoryMetadata(
        category=ReportCategory.EQUIPMENT_DAMAGE,
        label_en="Damaged agricultural equipment",
        description_en=(
            "Tractor, thresher, storage facility or other agricultural "
            "equipment damaged by flooding."
        ),
        icon="🔧",
        requires_location=False,
        sensitive_location=True,
    ),
    CategoryMetadata(
        category=ReportCategory.WATER_CONTAMINATION,
        label_en="Contaminated water source",
        description_en=(
            "Drinking water source (well, hand pump, canal) contaminated by "
            "floodwater, sewage, or agricultural chemicals."
        ),
        icon="⚠️",
        requires_location=False,
        sensitive_location=False,
    ),
    CategoryMetadata(
        category=ReportCategory.GENERAL_FLOOD_IMPACT,
        label_en="General flood impact",
        description_en=(
            "Other flood-related impact not covered by the specific "
            "categories above."
        ),
        icon="🌊",
        requires_location=False,
        sensitive_location=False,
    ),
)


def get_category_metadata(category: ReportCategory) -> CategoryMetadata | None:
    """Look up metadata for a report category."""
    for meta in CATEGORY_REGISTRY:
        if meta.category == category:
            return meta
    return None


# Privacy and consent constants for future intake design.
# These define the minimum requirements but do NOT enable submission.
CONSENT_REQUIREMENTS = {
    "data_minimization": (
        "Collect only the minimum information needed for the report. "
        "Do not require exact farm coordinates unless specifically needed "
        "and consented to."
    ),
    "location_privacy": (
        "Reports with sensitive_location=True must not expose precise "
        "farm or household coordinates publicly. Coarsen to district or "
        "corridor level for any public display."
    ),
    "submission_acknowledgement": (
        "Every accepted report must receive a stable receipt ID. "
        "The submitter must be able to check report status using this ID."
    ),
    "moderation_transparency": (
        "Report status transitions (submitted → under_review → verified | "
        "rejected | needs_info) must be audited with timestamps."
    ),
    "retention_policy": (
        "Define and communicate a data retention period. "
        "Reports must not be retained indefinitely without policy."
    ),
    "no_automatic_forwarding": (
        "Reports must not be forwarded to government agencies or third "
        "parties without explicit authorized integration and consent."
    ),
}
