from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

PUBLIC_DISCLAIMER = (
    "For situational awareness only. Follow NDMA/PDMA and district authority instructions for warnings, "
    "evacuations, and response actions."
)
PUBLIC_DISCLAIMER_UR = (
    "یہ صرف صورتحال سے آگاہی کے لیے ہے۔ انتباہات، انخلا، اور ہنگامی اقدامات کے لیے NDMA/PDMA "
    "اور ضلعی انتظامیہ کی ہدایات پر عمل کریں۔"
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _required(data: dict[str, Any], field: str) -> Any:
    value = data.get(field)
    if value in (None, "", []):
        raise ValueError(f"missing required field: {field}")
    return value


def render_alert_template(*, event: dict[str, Any], variant: str, template_name: str = "ndma_pdma_flood_alert_v1") -> dict[str, Any]:
    if variant not in {"official_internal", "public_safe"}:
        raise ValueError("variant must be official_internal or public_safe")

    event_id = _required(event, "event_id")
    aoi = _required(event, "aoi")
    status = _required(event, "status")
    timestamps = _required(event, "timestamps")
    detected_at = _required(timestamps, "detected_at")
    confidence_breakdown = _required(event, "confidence_breakdown")
    confidence_score = confidence_breakdown.get("score", confidence_breakdown.get("final_confidence"))
    if confidence_score in (None, "", []):
        raise ValueError("missing required field: score")
    confidence_label = _required(event, "confidence_bucket")
    lineage = event.get("lineage") or {}

    payload: dict[str, Any] = {
        "template": template_name,
        "variant": variant,
        "event_id": event_id,
        "aoi": aoi,
        "status": status,
        "generated_at": _utc_now_iso(),
        "event_timestamp": detected_at,
        "affected_area": {
            "corridor": aoi,
            "geometry": event.get("geometry"),
            "district": event.get("exposure", {}).get("district"),
        },
        "confidence": {
            "score": confidence_score,
            "label": confidence_label,
            "method": confidence_breakdown.get("method"),
            "breakdown": confidence_breakdown,
        },
        "limitations": {
            "summary": "Model- and data-driven flood indications can be delayed or uncertain.",
            "lineage_available": bool(lineage),
        },
        "recommended_actions": [
            "Coordinate with district administration and emergency operations centers.",
            "Validate inundation extent with field teams and partner observations.",
            "Prepare evacuation and relief routes for vulnerable communities.",
        ],
        "source_lineage": {
            "source_scene_ids": lineage.get("source_scene_ids", []),
            "processing_version": lineage.get("processing_version"),
            "thresholds": lineage.get("thresholds", {}),
        },
    }

    if variant == "public_safe":
        payload["public_disclaimer"] = PUBLIC_DISCLAIMER
        payload["public_disclaimer_ur"] = PUBLIC_DISCLAIMER_UR
        payload["localized"] = {
            "languages_supported": ["en", "ur"],
            "default_language": "en",
            "rtl_languages": ["ur"],
            "disclaimer": {
                "en": PUBLIC_DISCLAIMER,
                "ur": PUBLIC_DISCLAIMER_UR,
            },
            "limitations_summary": {
                "en": payload["limitations"]["summary"],
                "ur": "ماڈل اور ڈیٹا پر مبنی سیلابی اشارے تاخیر یا غیر یقینی کا شکار ہو سکتے ہیں۔",
            },
            "recommended_actions": {
                "en": [
                    "Monitor official NDMA/PDMA and district advisories.",
                    "Avoid floodwater crossings and low-lying routes.",
                    "Keep emergency supplies and family communication plans ready.",
                ],
                "ur": [
                    "NDMA/PDMA اور ضلعی انتظامیہ کی سرکاری ہدایات پر نظر رکھیں۔",
                    "سیلابی پانی اور نشیبی راستوں سے گزرنے سے گریز کریں۔",
                    "ہنگامی سامان اور خاندانی رابطہ منصوبہ تیار رکھیں۔",
                ],
            },
        }
        payload["limitations"]["reference"] = "/public/limitations"
        payload["recommended_actions"] = [
            "Monitor official NDMA/PDMA and district advisories.",
            "Avoid floodwater crossings and low-lying routes.",
            "Keep emergency supplies and family communication plans ready.",
        ]
    else:
        payload["workflow"] = {
            "approval_trace": event.get("approval_trace", []),
            "analyst_notes": event.get("notes", ""),
        }

    return payload
