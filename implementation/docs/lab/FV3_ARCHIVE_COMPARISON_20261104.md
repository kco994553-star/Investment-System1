# Offline v3 archive comparison / 1

Status: the existing `validation.forward_ledger` and `tools/forward_validation_ledger.py` still implement operating v1/v2. #442 and #451 approved v3's design, not a completed v3 operating engine. This first offline step implements the archived-public-QGV vs PIT-reconstructed-QGV diagnostic. No operating switch, scheduled collection, returns or ledger migration is included.

```
python implementation/tools/fv3_archive_compare.py --archive <qgv-official.json> \
  [--identity-links <dated-links.json>] [--reconstructed <pit-qgv.json>] \
  --output <new-private-file>
```

The existing official reader and coverage adapter validate the archive. Missing optional evidence is reported, not filled. Every supplied file is hashed. Code membership, input vintage and price basis stay separate; an archive generated after its price date is not certified as information available on that date.

`dated-security-links/1`: `links` contains code, security_id, namespace, valid_from, valid_to (exclusive, or null), evidence. Namespace is canonical uppercase ASCII (`[A-Z][A-Z0-9_.:/-]{0,63}`), without whitespace. CIK/TICKER/ISSUER/COMPANY_ID are forbidden in links and reconstructed rows. Expired and ambiguous links do not create security IDs, including collisions originating from a code with multiple links. No join is inferred from a common issuer or ticker.

`fv3-pit-qgv/1`: `rows` contains security_id, namespace, as_of, calc_version, scores `{Q,G,V,total}` (0–100 or null), input_manifest_sha256, source_commit. The upstream existing calculation engine supplies these scores; this tool does not implement another QGV formula. Duplicate security/date/version keys are rejected. The contents of upstream PIT manifests are not audited here; `pit_reconstruction_certified=false` makes this scope explicit.

Comparison key: namespace + fixed security ID + date + calculation version. Different dates/versions are unmatched with a reason. Score differences are `reconstructed - archived`, in score points. Missing scores remain null. Sample ranks use only the exact common set with both totals, descending unrounded totals and namespace/security ID tie-break. Rank difference is after minus before; valid N is explicit. These are sample diagnostics, not operational-rank agreement or market ranks.

Output includes counts for archived codes, identity links, reconstruction rows, matched securities, each comparable axis and total; per-row reasons, input hashes and archive times. No evidence means 0 comparisons, not zero scores. The complete historical-market denominator remains null.

Main handoff: result kind SAMPLE_DIAGNOSTIC, as_of, calc_version, valid N, count units, score-point deltas and missing reason fields. Synthetic test: two distinct securities of one issuer change totals 80→50 and 60→70, differences −30/+10 and sample rank changes +1/−1. Real rows stay private. Existing Lab v2 accepts count/fraction summaries only; detailed comparison is a private research artifact, not an unsolicited screen contract change.

v3's monthly PIT issuer top-500 population is separate from 9.1's C2 scoring and U-A/U-B annual next-open execution. Unresolved policies are not implemented by this diagnostic.
