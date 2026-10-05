# Investment-System1 · PIW_DECISION_RECORDS

Append-only record of decisions the Primary Integration Writer takes under delegated authority (CDR-015, D2). Single writer: the Primary Integration Writer. User decisions are recorded verbatim in `COORDINATION_DECISION_REGISTER.md`, not here; capability owners record their own D2 decisions in their scoped Decision Registers.

Rules: never edit or delete an entry. A later decision that changes an earlier one is a new entry naming the entry it supersedes. Every entry states:

- **Decision** and the authority it rests on (a CDR entry).
- **Reason**: requirements, the alternatives considered, and why this one.
- **Impact**: what changes, for whom, and what is not claimed.
- **Verification**: the evidence (GIE, commits, CI runs) that supports it, and what is still unverified.
- **Recovery**: how to reverse or supersede it, and what cannot be reversed.

A decision here never rewrites Frozen records or history, never hides a failure or unverified scope, and is not an approval of anything outside its stated scope. D3 (paid payment, paid subscription, extra charges, exceeding a free quota) is never decided here.

---
