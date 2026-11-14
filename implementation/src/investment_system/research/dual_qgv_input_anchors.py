"""Bind two retained inputs to an independently pinned preservation manifest.

No scoring, reconstruction, or conversion of run-lineage metadata into proof.
The root hash must be obtained from the earlier preservation handoff, never from
the result delivery that is being checked.
"""
from copy import deepcopy
import hashlib
import json

from .dual_qgv_delivery import require, validate_input_bindings
from .sector_qgv_reference import _identity, _records


SCHEMA = 'qgv-dual-input-anchors/1'


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _listed(raw, manifest, path):
    matches = [f for f in manifest['files'] if f['path'] == path]
    require(len(matches) == 1, 'SOURCE_MEMBER_NOT_UNIQUE')
    require(matches[0]['size'] == len(raw) and matches[0]['sha256'] == _sha(raw),
            'SOURCE_MEMBER_HASH')
    return deepcopy(matches[0])


def input_anchors(*, scope, preservation, handoff_raw, bundle_raw,
                  expected_handoff_sha256, evaluation_raw, evaluation_path,
                  reference_raw, reference_path):
    require(scope in ('operating504', 'held1057'), 'SCOPE')
    require(_sha(handoff_raw) == expected_handoff_sha256, 'PRESERVATION_ROOT_HASH')
    handoff = json.loads(handoff_raw)
    require(handoff.get('schema_version') == 'qgv-q-input-handoff/1', 'PRESERVATION_SCHEMA')
    require(all(handoff.get(k) == preservation.get(k) for k in ('repo', 'ref', 'path')),
            'PRESERVATION_LOCATION')
    bundle_descriptor = _listed(bundle_raw, handoff, 'bundle-manifest.json')
    bundle = json.loads(bundle_raw)
    require(bundle.get('schema_version') == 'qgv-q-input-private-bundle/1', 'BUNDLE_SCHEMA')
    source_files = {
        'evaluation': _listed(evaluation_raw, bundle, evaluation_path),
        'reference': _listed(reference_raw, bundle, reference_path),
    }
    ev, ref = json.loads(evaluation_raw), json.loads(reference_raw)
    require(ev.get('schema_version') == ref.get('schema_version') == 'sector-qgv-input/1',
            'INPUT_SCHEMA')
    # The two inputs may have different construction/version chains. Their own
    # hashes bind those chains; only the engine's shared temporal context agrees.
    for key in ('valuation_date', 'as_of', 'mapping_version'):
        require(ev.get(key) == ref.get(key), 'INPUT_CONTEXT')
    er, rr = _records(ev), _records(ref)
    require(all(k in rr and v == rr[k] for k, v in er.items()), 'TARGET_ROW_PROJECTION')
    changes = sorted(k for k in ev.keys() | ref.keys() if ev.get(k) != ref.get(k))
    # Review-context source hashes legitimately differ. Record the actual delta;
    # never claim the old five-field projection contract applies to these inputs.
    return dict(schema_version=SCHEMA, scope=scope,
        expected_evaluation=_identity(ev), expected_reference=_identity(ref),
        preservation={**deepcopy(preservation), 'handoff_manifest_sha256': expected_handoff_sha256,
                      'bundle_manifest': bundle_descriptor},
        source_files=source_files, execution_sha=bundle['execution_sha'],
        projection=dict(rows_equal_source_projection=True, changed_top_level_fields=changes,
                        review_context_equal=ev.get('review_context') == ref.get('review_context'),
                        claim='ROW_PROJECTION_ONLY;INPUT_IDENTITIES_INDEPENDENTLY_BOUND'),
        generation_rule='PINNED_RETAINED_SNAPSHOT_BYTES_TO_EXISTING_IDENTITY_FUNCTION',
        runtime_lineage_used_as_proof=False, new_score_calculations=0,
        whole_market_denominator=None)


def validate_anchored_delivery(summary, index, *, anchor_raw, expected_anchor_sha256):
    """The anchor pin is installed by staging from the independent source handoff."""
    require(_sha(anchor_raw) == expected_anchor_sha256, 'INPUT_ANCHOR_HASH')
    anchor = json.loads(anchor_raw)
    require(anchor.get('schema_version') == SCHEMA, 'INPUT_ANCHOR_SCHEMA')
    return validate_input_bindings(summary, index,
        expected_evaluation=anchor['expected_evaluation'],
        expected_reference=anchor['expected_reference'])


def delivery_clocks(*, generated_at, execution_sha, inspected_record_refs):
    """For retained runs whose own execution records contain no clock field.

    This function deliberately accepts no file/commit timestamp fallback.
    Future runs should record their actual execution clocks at execution time.
    """
    from .sector_qgv import timestamp
    timestamp(generated_at)
    require(bool(inspected_record_refs), 'EXECUTION_RECORDS_REQUIRED')
    return dict(schema_version='qgv-dual-delivery-clocks/1',
        execution_sha=execution_sha, calculated_at=None,
        calculated_at_reason='EXECUTION_TIMESTAMP_NOT_RECORDED',
        inspected_execution_records=deepcopy(inspected_record_refs),
        delivery_generated_at=generated_at, new_score_calculations=0)
