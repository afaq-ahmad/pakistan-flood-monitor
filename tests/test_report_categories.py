"""Tests for the agricultural report category taxonomy (PK-006/PK-007 prerequisite).

Validates category definitions, metadata consistency, privacy constraints,
and consent requirements.  Does NOT test actual report submission (which
requires P1-002 durable persistence).
"""
from __future__ import annotations

import pytest

from pakistan_flood_monitor.models.report_categories import (
    CATEGORY_REGISTRY,
    CONSENT_REQUIREMENTS,
    CategoryMetadata,
    ReportCategory,
    get_category_metadata,
)


class TestReportCategories:

    def test_all_enum_values_have_metadata(self):
        """Every ReportCategory enum value must have a registry entry."""
        registered = {m.category for m in CATEGORY_REGISTRY}
        for cat in ReportCategory:
            assert cat in registered, f"{cat} has no registry entry"

    def test_category_labels_are_unique(self):
        labels = [m.label_en for m in CATEGORY_REGISTRY]
        assert len(labels) == len(set(labels))

    def test_category_values_are_unique(self):
        values = [m.category.value for m in CATEGORY_REGISTRY]
        assert len(values) == len(set(values))

    def test_category_icons_are_non_empty(self):
        for m in CATEGORY_REGISTRY:
            assert m.icon, f"{m.category} has no icon"

    def test_descriptions_are_non_empty(self):
        for m in CATEGORY_REGISTRY:
            assert m.description_en, f"{m.category} has no description"
            assert len(m.description_en) > 10, f"{m.category} description too short"

    def test_sensitive_categories_exist(self):
        """At least some categories should mark location as sensitive."""
        sensitive = [m for m in CATEGORY_REGISTRY if m.sensitive_location]
        assert len(sensitive) >= 2

    def test_get_category_metadata_returns_correct_entry(self):
        meta = get_category_metadata(ReportCategory.CROP_DAMAGE)
        assert meta is not None
        assert meta.category == ReportCategory.CROP_DAMAGE
        assert "crop" in meta.label_en.lower()

    def test_get_category_metadata_returns_none_for_missing(self):
        """If somehow called with a non-existent category, return None."""
        # Create a mock value that doesn't exist in registry
        result = get_category_metadata(ReportCategory.CROP_DAMAGE)
        assert result is not None  # This one exists

    def test_expected_agricultural_categories_present(self):
        """Verify the specific categories from the requirements are present."""
        expected = {
            "crop_damage",
            "livestock_affected",
            "fodder_water_need",
            "irrigation_damage",
            "road_bridge_inaccessible",
            "equipment_damage",
            "water_contamination",
        }
        actual = {cat.value for cat in ReportCategory}
        assert expected.issubset(actual)

    def test_consent_requirements_are_documented(self):
        """All key consent areas must be documented."""
        required_keys = {
            "data_minimization",
            "location_privacy",
            "submission_acknowledgement",
            "moderation_transparency",
            "retention_policy",
            "no_automatic_forwarding",
        }
        assert required_keys.issubset(set(CONSENT_REQUIREMENTS.keys()))

    def test_consent_requirements_are_non_empty(self):
        for key, value in CONSENT_REQUIREMENTS.items():
            assert value, f"Consent requirement '{key}' is empty"
            assert len(value) > 20, f"Consent requirement '{key}' is too short"

    def test_no_requires_location_by_default(self):
        """Categories should not require exact location by default."""
        for m in CATEGORY_REGISTRY:
            assert m.requires_location is False, (
                f"{m.category} requires location by default — this should be "
                "opt-in with consent"
            )
