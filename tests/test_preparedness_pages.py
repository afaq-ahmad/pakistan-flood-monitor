"""Tests for the Farmer and Livestock Preparedness pages (PK-007 prerequisite).

Offline and deterministic — no network, no credentials, no live data.
Verifies that pages render, demo watermark appears correctly, and that
content does not fabricate observations or claim service availability.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "streamlit_app.py"
FARMER_PAGE = next((ROOT / "pages").glob("17_*")).relative_to(ROOT)
LIVESTOCK_PAGE = next((ROOT / "pages").glob("18_*")).relative_to(ROOT)


@pytest.fixture
def dashboard(monkeypatch):
    import backend_service

    monkeypatch.setattr(backend_service, "API_BASE_URL", None)
    monkeypatch.setattr(backend_service, "_APP_MODE", "demo")
    return backend_service


# ── Farmer Preparedness ──────────────────────────────────────────────────────

class TestFarmerPreparedness:

    def test_farmer_page_renders_without_exception(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        assert not page.exception

    def test_farmer_page_shows_demo_watermark(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        assert any(
            dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value
            for w in page.warning
        )

    def test_farmer_page_no_demo_watermark_in_operational(self, dashboard, monkeypatch):
        monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        assert not any(
            dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value
            for w in page.warning
        )

    def test_farmer_page_has_official_link(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        page_links = page.get("page_link")
        assert any(pl.proto.page == "Official_Information" for pl in page_links)

    def test_farmer_page_contains_key_sections(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        headers = [h.value for h in page.header]
        assert any("Before" in h for h in headers)
        assert any("During" in h for h in headers)
        assert any("After" in h or "Recovery" in h for h in headers)
        assert any("Resources" in h for h in headers)

    def test_farmer_page_does_not_fabricate_observations(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        # No metric, dataframe or map should appear — this is guidance only.
        assert not page.metric
        assert not page.dataframe

    def test_farmer_page_has_limitations(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        expanders = [e.label for e in page.expander]
        assert any("Limitations" in e for e in expanders)

    def test_farmer_page_mentions_urdu_subtask(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        all_text = " ".join(
            m.value for m in page.markdown
        )
        assert "Urdu" in all_text


    def test_farmer_checklists_and_print_view(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(FARMER_PAGE)).run()
        assert not page.exception
        assert [header.value for header in page.header[:3]] == [
            "Before flooding", "During flooding", "After flooding",
        ]
        assert any("portable pumps" in block.value for block in page.main.markdown)
        assert any(detail.label == "Crops, equipment and chemicals" for detail in page.expander)

        page.checkbox[0].check().run()
        assert not page.exception
        assert not page.expander
        assert any(heading.value == "Crops, equipment and chemicals" for heading in page.subheader)
        assert any("University of Vermont Extension" in block.value for block in page.markdown)
        assert any("FAO Pakistan" in block.value for block in page.markdown)


# ── Livestock Preparedness ───────────────────────────────────────────────────

class TestLivestockPreparedness:

    def test_livestock_page_renders_without_exception(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        assert not page.exception

    def test_livestock_page_shows_demo_watermark(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        assert any(
            dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value
            for w in page.warning
        )

    def test_livestock_page_no_demo_watermark_with_api(self, dashboard, monkeypatch):
        monkeypatch.setattr(dashboard, "API_BASE_URL", "http://api.test")
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        assert not any(
            dashboard.DEMO_WATERMARK.removeprefix("⚠️ ") in w.value
            for w in page.warning
        )

    def test_livestock_page_has_official_link(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        page_links = page.get("page_link")
        assert any(pl.proto.page == "Official_Information" for pl in page_links)

    def test_livestock_page_contains_key_sections(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        headers = [h.value for h in page.header]
        assert any("Before" in h for h in headers)
        assert any("During" in h for h in headers)
        assert any("After" in h or "Recovery" in h for h in headers)
        assert any("Resources" in h for h in headers)

    def test_livestock_page_does_not_fabricate_observations(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        assert not page.metric
        assert not page.dataframe

    def test_livestock_page_has_limitations(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        expanders = [e.label for e in page.expander]
        assert any("Limitations" in e for e in expanders)

    def test_livestock_page_does_not_claim_service_availability(self, dashboard):
        """Ensure no unverified claims about shelter/vet service availability."""
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        all_text = " ".join(m.value for m in page.markdown)
        # Should warn about unverified services, not claim they are open.
        assert "cannot verify" in all_text or "cannot confirm" in all_text

    def test_livestock_page_mentions_urdu_subtask(self, dashboard):
        page = AppTest.from_file(HOME).switch_page(str(LIVESTOCK_PAGE)).run()
        all_text = " ".join(m.value for m in page.markdown)
        assert "Urdu" in all_text
