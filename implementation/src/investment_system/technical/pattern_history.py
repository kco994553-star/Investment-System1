"""Official pattern detection history (§8.4-§8.7, P1-6). Python reference for web_assets/pattern-history.js.

RAM only (session record; owner decision Q2 keeps durable storage for phase 2). Append only: a record is never
changed or removed. One history per (symbol, timeframe, rule_version, params_sha256); a run of another version is
refused, never mixed. Only OFFICIAL runs are accepted: user settings and user drawings never touch it (§11.4).
An object enters only when its first transition was judgeable (continuity CONFIRMED); its later transitions,
including NOT_JUDGEABLE, follow it. Data revisions add DATA_REVISION records; earlier records stay as they were.
"""
from __future__ import annotations

import copy
import json

SCHEMA = 'pattern-history/1'
REVISION_NOTE_KO = '자료 수정 후 재계산 결과 다름'
_KEY_FIELDS = ('object_id', 'event', 'known_at')
_CONTENT = ('object_id', 'object_kind', 'pattern', 'event', 'state', 'timeframe', 'rule_version', 'params_sha256',
            'anchor_index', 'anchor_at', 'known_index', 'known_at', 'detail', 'judgement', 'superseded_by')


class PatternHistoryError(ValueError):
    pass


def _canon(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _content(tr):
    return {k: tr[k] for k in _CONTENT if k in tr}


def _eligible(first):
    return first['event'] != 'NOT_JUDGEABLE' and first['judgement']['state'] == 'CONFIRMED'


class PatternHistory:
    def __init__(self, symbol, timeframe, rule_version, params_sha256):
        self.key = {'symbol': symbol, 'timeframe': timeframe, 'rule_version': rule_version, 'params_sha256': params_sha256}
        self._records, self._keys, self._decided = [], {}, {}

    def _check(self, result):
        if result.get('run_mode') != 'OFFICIAL':
            raise PatternHistoryError('HISTORY_USER_SETTINGS_REFUSED')
        if {k: result.get(k) for k in self.key} != self.key:
            raise PatternHistoryError('HISTORY_VERSION_MIXED')

    def _latest(self):
        days = [r['known_at'] for r in self._records if r['event'] != 'DATA_REVISION']
        return max(days) if days else None

    def _push(self, record, computed_at):
        record = {**copy.deepcopy(record), 'seq': len(self._records) + 1, 'computed_at': computed_at}
        self._records.append(record)
        self._keys['|'.join(str(record[k]) for k in _KEY_FIELDS)] = record

    def append(self, result, computed_at):
        """Adds the transitions of an official run that are not recorded yet. Returns counts only.

        A recorded object whose recomputed past (known_at <= the latest recorded date) differs from its records is
        diverged: nothing of it is added (`conflicts`); a data revision goes through record_revision instead. A new
        object that would start on or before the latest recorded date is back-dated and withheld (`late`, §13.1).
        """
        self._check(result)
        counts = {'added': 0, 'duplicates': 0, 'withheld': 0, 'conflicts': 0, 'late': 0}
        latest = self._latest()
        recorded, runs = {}, {}
        for r in self._records:
            if r['event'] != 'DATA_REVISION':
                recorded.setdefault(r['object_id'], []).append(_canon(_content(r)))
        for tr in result['transitions']:
            if latest is not None and tr['known_at'] <= latest:
                runs.setdefault(tr['object_id'], []).append(_canon(_content(tr)))
        diverged = {oid for oid, seq in recorded.items() if runs.get(oid, []) != seq}
        late = set()
        for tr in result['transitions']:
            oid = tr['object_id']
            if oid not in self._decided:
                self._decided[oid] = _eligible(tr)
            if not self._decided[oid]:
                counts['withheld'] += 1
            elif oid in diverged:
                counts['conflicts'] += 1
            elif '|'.join(str(tr[k]) for k in _KEY_FIELDS) in self._keys:
                counts['duplicates'] += 1
            elif oid in late or (oid not in recorded and latest is not None and tr['known_at'] <= latest):
                late.add(oid)
                counts['late'] += 1
            else:
                self._push(_content(tr), computed_at)
                recorded.setdefault(oid, [])
                counts['added'] += 1
        return counts

    def record_revision(self, official, revised, revised_dates, known_at, computed_at):
        """§8.6: compare an object's transitions on held data and on revised data; differences add DATA_REVISION."""
        self._check(official)
        self._check(revised)
        def by_object(result):
            out = {}
            for tr in result['transitions']:
                out.setdefault(tr['object_id'], []).append(_canon(_content(tr)))
            return out
        a, b = by_object(official), by_object(revised)
        affected = []
        for oid in sorted({r['object_id'] for r in self._records}):
            if a.get(oid) != b.get(oid):
                affected.append(oid)
                key = '|'.join((oid, 'DATA_REVISION', str(known_at)))
                if key in self._keys:
                    continue
                first = next(r for r in self._records if r['object_id'] == oid)
                self._push({'object_id': oid, 'object_kind': first['object_kind'], 'pattern': first.get('pattern'), 'event': 'DATA_REVISION',
                            'state': None, 'timeframe': self.key['timeframe'], 'rule_version': self.key['rule_version'],
                            'params_sha256': self.key['params_sha256'], 'anchor_index': first['anchor_index'], 'anchor_at': first['anchor_at'],
                            'known_index': None, 'known_at': known_at,
                            'detail': {'revised_dates': sorted(revised_dates), 'note_ko': REVISION_NOTE_KO, 'recomputed': 'DIFFERENT' if oid in b else 'ABSENT'},
                            'judgement': None}, computed_at)
        return {'affected': affected}

    def records(self):
        return copy.deepcopy(self._records)


class PatternHistoryBook:
    """Histories kept apart by symbol, timeframe, rule version and parameter hash; older versions stay as they are."""

    def __init__(self):
        self._items = {}

    def history_for(self, result):
        key = (result['symbol'], result['timeframe'], result['rule_version'], result['params_sha256'])
        if key not in self._items:
            self._items[key] = PatternHistory(*key)
        return self._items[key]

    def append(self, result, computed_at):
        if result.get('run_mode') != 'OFFICIAL':
            raise PatternHistoryError('HISTORY_USER_SETTINGS_REFUSED')
        return self.history_for(result).append(result, computed_at)

    def keys(self):
        return [list(k) for k in sorted(self._items)]

    def clear(self):
        self._items.clear()
