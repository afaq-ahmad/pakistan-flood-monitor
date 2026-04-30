# Damage Classification (Housing + Infrastructure)

Schema: `damage-classification/v1`.

## Classes
- `none`: below minor threshold.
- `minor`
- `moderate`
- `major`

## Feature inputs
- Housing: exposed population proxy.
- Infrastructure: exposed roads km + facility count weighted score.
- Confidence: average of flood probability, breach risk, and final event confidence.
- Uncertainty: `1 - confidence`.

## Lineage fields
Each district row includes:
- `lineage.model`
- `lineage.model_version`
- `lineage.generated_at`
- `lineage.inputs`

## Assumptions and limitations
- Rule-based adapter is a deterministic baseline, not a learned per-asset damage model.
- Exposure-quality errors propagate into damage classes.
- Benchmark validation is currently sample-based and should be replaced with curated labeled events.
