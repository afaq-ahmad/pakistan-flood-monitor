from urllib.parse import urlparse

from official_sources import OFFICIAL_SOURCES, SOURCE_REVIEWED_ON


def test_directory_is_static_attributed_and_https():
    assert SOURCE_REVIEWED_ON == "2026-11-18"
    assert len(OFFICIAL_SOURCES) == 2
    hosts = {urlparse(item["url"]).hostname for item in OFFICIAL_SOURCES}
    assert hosts == {"ffd.weather.gov.pk", "www.ndma.gov.pk"}
    for source in OFFICIAL_SOURCES:
        assert all(source[key] for key in ("name", "purpose", "coverage", "url"))
        assert urlparse(source["url"]).scheme == "https"
