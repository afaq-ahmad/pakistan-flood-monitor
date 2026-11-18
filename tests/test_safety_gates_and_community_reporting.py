"""Tests for operational safety gates (FL-08), hydromet reporting (FL-09),
historical disclaimers (FL-03), and community report intake (PK-006).

Deterministic and offline — no network, no live model execution.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
PAGE_FORECAST = next((ROOT / "pages").glob("13_*")).relative_to(ROOT)
PAGE_DAM = next((ROOT / "pages").glob("15_*")).relative_to(ROOT)
PAGE_HISTORICAL = next((ROOT / "pages").glob("12_*")).relative_to(ROOT)
PAGE_HYDROMET = next((ROOT / "pages").glob("10_*")).relative_to(ROOT)
PAGE_REPORTS = next((ROOT / "pages").glob("3_*")).relative_to(ROOT)


@pytest.fixture
def dashboard(monkeypatch):
    import backend_service
    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
    return backend_service


# ── FL-08: Predictive Forecast Operational Safety Gate ───────────────────────

class TestForecastSafetyGate:

    def test_forecast_fails_closed_in_operational_mode(self, dashboard, monkeypatch):
        monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
        monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
        page = AppTest.from_file(HOME).switch_page(str(PAGE_FORECAST)).run()

        assert not page.exception
        assert any("unavailable in operational mode" in err.value for err in page.error)
        # Verify no forecast parameters or run controls leaked in operational mode
        all_text = " ".join(m.value for m in page.markdown)
        assert "evacuation" not in all_text.lower()
        assert "EARLY WARNING ALERT" not in all_text

    def test_forecast_demo_mode_displays_watermark_and_no_evacuation_directive(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_FORECAST)).run()

        assert not page.exception
        assert any(dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value for w in page.warning)
        all_text = " ".join(m.value for m in page.markdown)
        assert "evacuation notices" not in all_text.lower()

    def test_forecast_has_official_link(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_FORECAST)).run()
        page_links = page.get("page_link")
        assert any("Official" in pl.proto.label for pl in page_links)


# ── FL-08: Dam-Aware Risk Operational Safety Gate ────────────────────────────

class TestDamRiskSafetyGate:

    def test_dam_risk_fails_closed_in_operational_mode(self, dashboard, monkeypatch):
        monkeypatch.setattr(dashboard, "_APP_MODE", "operational")
        monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
        page = AppTest.from_file(HOME).switch_page(str(PAGE_DAM)).run()

        assert not page.exception
        assert any("unavailable in operational mode" in err.value for err in page.error)
        all_text = " ".join(m.value for m in page.markdown)
        assert "DAM-AWARE ALERT" not in all_text

    def test_dam_risk_demo_mode_displays_watermark(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_DAM)).run()

        assert not page.exception
        assert any(dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value for w in page.warning)

    def test_dam_risk_has_official_link(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_DAM)).run()
        page_links = page.get("page_link")
        assert any("Official" in pl.proto.label for pl in page_links)


# ── FL-03: Historical Flood Map Disclaimer ───────────────────────────────────

class TestHistoricalMapDisclaimer:

    def test_historical_map_disclaimer_replaces_ground_truth_claim(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_HISTORICAL)).run()

        assert not page.exception
        all_text = " ".join(
            [m.value for m in page.markdown] + [i.value for i in page.info]
        )
        assert "ground-truth targets" not in all_text
        assert "approximate" in all_text.lower()
        assert any("Historical flood extents are approximate" in c.value for c in page.caption)

    def test_historical_map_shows_demo_watermark(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_HISTORICAL)).run()
        assert any(dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value for w in page.warning)


# ── PK-006 / FL-05: Community Report Intake ──────────────────────────────────

class TestCommunityReportIntake:

    @pytest.fixture
    def demo_env(self, monkeypatch, tmp_path):
        import backend_service
        monkeypatch.setattr(backend_service, "API_BASE_URL", None)
        monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
        monkeypatch.setattr(backend_service, "DATA_DIR", tmp_path)
        path = tmp_path / "field_reports.csv"
        import pandas as pd
        pd.DataFrame([{
            "report_id": "demo-report",
            "event_id": "demo-event",
            "observed_at": "2026-01-02T10:00:00Z",
            "latitude": 28.0,
            "longitude": 69.0,
            "reporter_channel": "fixture",
            "status": "submitted",
            "trusted": False,
            "moderation_tags": "",
            "notes": "synthetic demo note",
        }]).to_csv(path, index=False)
        return backend_service

    def test_community_submission_requires_consent(self, demo_env):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        assert not page.exception

        # Fill in notes without checking consent
        page.text_area(key="sub_notes").input("Submerged irrigation canal near village").run()
        page.button(key="sub_submit_btn").click().run()

        assert any("Consent is required" in err.value for err in page.error)

    def test_community_submission_generates_receipt_with_consent(self, demo_env):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        assert not page.exception

        page.text_area(key="sub_notes").input("Standing water in wheat fields").run()
        page.checkbox(key="sub_consent").check().run()
        page.button(key="sub_submit_btn").click().run()

        assert any("Report received" in s.value for s in page.success)
        assert any("REC-" in s.value for s in page.success)
        assert any("Pending Moderation" in info.value for info in page.info)


# ── FL-09: NASA Hydromet Counter Accuracy ────────────────────────────────────

class TestHydrometCounterAccuracy:

    def test_hydromet_reports_failure_not_success_on_error(self, dashboard, monkeypatch):
        import nasa_service
        monkeypatch.setattr(nasa_service, "fetch_corridor_rainfall", lambda corr, days: {"error": "Offline fixture error"})
        page = AppTest.from_file(HOME).switch_page(str(PAGE_HYDROMET)).run()
        assert not page.exception
        # Must show error, not false success
        assert any("failed to load" in err.value for err in page.error)
        assert not any("✅ NASA POWER data loaded for 6 corridors" in s.value for s in page.success)
