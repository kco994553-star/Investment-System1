# Free Cloud Write Contract v1

Status: READ-ONLY VALIDATION CANDIDATE
Authority: CDR-024
Paid resource: none

This contract defines the maximum future repository mutation surface for the
zero-paid PC-free automation experiment.

Allowed future branch:
- `automation/free-cloud-state-v1`

Allowed future path:
- `implementation/docs/coordination/automation_free/FREE_CLOUD_STATUS.json`

Everything else is denied by default.

In particular:
- canonical is denied
- Global is denied
- governance control files are denied
- owner implementation branches are denied
- methodology/numeric-policy changes are not representable by this write set

This document does **not** grant GitHub Actions `contents: write`.
The workflow remains `contents: read`; it only proves the scope contract and
negative cases. Adding repository write permission is a separate authority
decision and must not be inferred from this candidate.
