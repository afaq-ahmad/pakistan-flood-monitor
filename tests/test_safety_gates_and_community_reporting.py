"""Tests for operational safety gates (FL-08), hydromet reporting (FL-09),
historical disclaimers (FL-03), and community report intake (PK-006).

Deterministic and offline — no network, no live model execution.
"""
from __future__ import annotations

from datetime import date
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

    def test_practice_requires_acknowledgement(self, demo_env):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        page.button(key="sub_submit_btn").click().run()
        assert not page.exception
        assert any("Confirm" in err.value for err in page.error)
        assert not page.success

    def test_repeated_previews_leave_the_queue_unchanged(self, demo_env):
        path = demo_env.DATA_DIR / "field_reports.csv"
        before = path.read_bytes()
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        assert not page.text_area
        assert "preview" in page.button(key="sub_submit_btn").label.lower()
        category = page.selectbox(key="sub_cat").options[1]
        page.selectbox(key="sub_cat").select(category)
        page.selectbox(key="sub_corridor").select("Chenab-Middle")
        page.date_input(key="sub_date").set_value(date(2026, 1, 2))
        page.checkbox(key="sub_consent").check()
        for _ in range(2):
            page.button(key="sub_submit_btn").click().run()
            assert not page.exception
            preview = next(item.value for item in page.info if "Practice preview" in item.value)
            assert all(value in preview for value in (category, "Chenab-Middle", "2026-01-02"))
            assert "Nothing was submitted" in preview
            assert not page.success
            messages = " ".join(item.value for item in page.info)
            assert all(term not in messages for term in ("REC-", "Pending Moderation", "Report received"))
            assert page.metric[0].value == "1"
            assert path.read_bytes() == before

    def test_preview_without_date(self, demo_env):
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        page.checkbox(key="sub_consent").check()
        page.date_input(key="sub_date").set_value(None)
        page.button(key="sub_submit_btn").click().run()
        assert not page.exception
        assert any("Choose a date" in err.value for err in page.error)

    def test_preview_without_moderation_file(self, demo_env):
        path = demo_env.DATA_DIR / "field_reports.csv"
        path.unlink()
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        page.checkbox(key="sub_consent").check()
        page.button(key="sub_submit_btn").click().run()
        assert not page.exception
        assert any("Nothing was submitted" in i.value for i in page.info)
        assert any("Demo field reports are unavailable" in i.value for i in page.info)
        assert not path.exists()

    def test_no_configured_corridors_preserves_moderation(self, demo_env, monkeypatch):
        from pakistan_flood_monitor.config import settings
        monkeypatch.setattr(settings, "pilot_corridors", [])
        page = AppTest.from_file(HOME).switch_page(str(PAGE_REPORTS)).run()
        assert not page.exception
        assert any("No pilot corridors" in i.value for i in page.info)
        assert "sub_corridor" not in [widget.key for widget in page.selectbox]
        assert "sub_submit_btn" not in [widget.key for widget in page.button]
        assert page.button(key="mod_approve_demo-report")


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
