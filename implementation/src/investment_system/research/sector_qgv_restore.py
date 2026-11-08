"""Replay a sector setting only with its retained preview and original input.

The existing six-field saved record is unchanged. It is not enough by itself to
identify a historical run: the retained preview binds engine/input versions and
the snapshot binds formula variants and the original population. Legacy profiles
stay with their original engine; this adapter never migrates or selects a model.
"""
from __future__ import annotations

import copy

from .sector_qgv import digest, preview_qgv, save_user_config
from .sector_qgv_partial import assert_retained_preview


def replay_saved_config(saved, retained_preview, snapshot, request_id):
    """Return an unchanged config and a new preview, or refuse context drift.

All calculations use preview_qgv. A different input, model/policy/formula version,
population or result needs a separately identified new run, never a replay label.
No caller object or retained output is modified.
    """
    if not isinstance(saved, dict) or not isinstance(saved.get('config'), dict):
        raise ValueError('SAVED_CONFIG_INVALID')
    config = saved['config']
    expected = save_user_config(config, retained_preview,
                               request_id=retained_preview['request_id'],
                               expected_preview_id=retained_preview['preview_id'])
    if saved != expected:
        raise ValueError('SAVED_PREVIEW_MISMATCH')
    if retained_preview['preview_id'] != digest({'cache': retained_preview['cache_key'],
                                                 'request_id': retained_preview['request_id']}):
        raise ValueError('RETAINED_PREVIEW_ID_MISMATCH')
    assert_retained_preview(retained_preview, snapshot, config)
    replay = preview_qgv(config, snapshot, request_id)
    # Request identity changes; every numerical/context field must remain exact.
    omit = {'preview_id', 'request_id'}
    if ({k: v for k, v in replay.items() if k not in omit} !=
            {k: v for k, v in retained_preview.items() if k not in omit}):
        raise ValueError('SAVED_REPLAY_CONTEXT_OR_RESULT_MISMATCH')
    return {'config': copy.deepcopy(config), 'preview': replay}
