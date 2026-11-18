# Pakistan Flood Monitor — Remaining Work Documentation

This page preserves the PR #92 verification checkpoint. The
[master task plan](MASTER_TASK_PLAN.md) is the authoritative pending and
blocked work list. Use the [implementation ledger](IMPLEMENTATION_STATUS.md)
for current evidence and limitations.

## Historical checkpoint · 18 November 2026

PR #92 replaced a demo form that displayed a receipt without saving or
queuing a report. Its preview is explicitly simulated. See
[the merged pull request](https://github.com/afaq-ahmad/pakistan-flood-monitor/pull/92).

## Findings and verification

| FL-05 end-user journey | Result at the checkpoint | Evidence |
|---|---|---|
| Preview a fictional agricultural report, then repeat | Practice form displays the selected category, configured corridor and date. No free-text identity field, receipt or queued status. | Streamlit AppTest checks UI output, total report count and unchanged CSV bytes on two consecutive actions. |
| Open Field Reports without usable moderation data | Practice is available independently. Fixture moderation displays unavailable. | Missing, empty and incomplete CSV cases. |
| Open Field Reports without configured coverage | Explicit unavailable message for practice. Existing fixture moderation is accessible. | AppTest with an empty corridor list. |
| Open in operational or API-backed mode | Resident intake and local moderation are unavailable. | Three mode combinations check for absent actions and zero CSV reads or mutations. |
| Submit a real report and track it through review | BLOCKED | The demo cannot issue a durable receipt. The authorized internal API does not offer private resident intake. |

Baseline 333 passed. Six focused acceptance cases failed before the page edit.
After implementation 29 focused tests and all 336 offline tests passed. See the
[QA matrix](../product/FARMER_LIVESTOCK_QA_MATRIX.md) for the other user journeys.
