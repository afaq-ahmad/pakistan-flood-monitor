# Rules V1 Evaluation Archive

This archived report records baseline rule performance before introducing a learned ranker.

- Flood candidate precision: 0.71
- Flood candidate recall: 0.78
- False alert rate: 0.19
- Analyst acceptance rate: 0.64

## Retraining triggers
Retraining is initiated only when one or more of the following occurs:
1. False alarms rise materially in reviewed events.
2. New labeled events increase data diversity.
3. New sensors or operational features are introduced.

A fixed calendar retraining schedule is intentionally not used.
