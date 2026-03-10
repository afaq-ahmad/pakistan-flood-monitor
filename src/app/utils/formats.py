from enum import StrEnum


class InternalRasterFormat(StrEnum):
    COG = "cog"


class InternalVectorFormat(StrEnum):
    GEOPARQUET = "geoparquet"
    POSTGIS = "postgis"


class ExternalPayloadFormat(StrEnum):
    GEOJSON = "geojson"
    JSON = "json"
