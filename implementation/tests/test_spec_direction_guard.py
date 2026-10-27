"""Direction guard + spec integrity (docs/SPEC). Offline, read-only."""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / 'docs' / 'SPEC'


def _guard():
    spec = importlib.util.spec_from_file_location('spec_direction_guard', ROOT / 'implementation' / 'tools' / 'spec_direction_guard.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_repository_has_no_superseded_direction_lines():
    hits = _guard().scan()
    assert hits == [], '\n'.join(f'{rid} {rel}:{n}: {line}' for rel, rid, n, line in hits)


def test_rules_catch_old_directions_and_pass_explanations():
    g = _guard()
    rules = g.load_rules()
    bad = [
        'Universe504는 미국 시가총액 상위 504 종목이다.',
        'Universe504 = S&P 500',
        'Universe504 is the S&P 500.',
        'Universe504 index-following rule applies on the effective date.',
        'V는 기기 전용이며 공개하지 않는다.',
        'V is device-only and is never published.',
        '균형형 = Q34/G33/V33',
        'QGV 점수는 로그인해야 보인다.',
        'Universe504 목록은 시트 연결이 필요하다.',
        'TARGET 목록은 기기에 저장된 값이 있어야 보인다.',
    ]
    good = [
        'Universe504는 S&P 500 구성에서 출발한 고정 목록이다(UNI-DEF).',
        'Universe504는 시가총액 상위 504가 아니다.',
        '"V는 기기 전용·비공개" 규칙은 이 결정으로 바뀐다(GSQ-024).',
        'Saved on this device only.',
        'diagnostics (V-SHARES-SCALE reason codes); never published.',
        '`balanced = Q34/G33/V33`은 균형형의 확정 정의가 아니다.',
        'QGV 점수는 로그인 없이도 처음 쓰는 기기에서 같게 보인다(DC-22).',
        'Universe504 목록은 공개 파일이고, 가격 불러오기에는 로그인과 가격 시트 연결이 필요하다.',
        '사용자 QGV 가중치는 기기에 저장한 값이 있어야 미리보기를 한다.',
    ]
    for line in bad:
        assert g.scan_text(line, rules), line
    for line in good:
        assert not g.scan_text(line, rules), line


def test_function_hierarchy_original_is_unchanged():
    text = (SPEC / 'FUNCTION_HIERARCHY_v1.0.md').read_text(encoding='utf-8')
    recorded = re.match(r'<!-- SPEC-ORIGINAL sha256=([0-9a-f]{64}) -->', text).group(1)
    body = text.split('\n---\n', 1)[1]
    assert hashlib.sha256(body.encode('utf-8')).hexdigest() == recorded


def test_direction_register_lists_every_rule():
    rules = json.loads((SPEC / 'direction_rules.json').read_text(encoding='utf-8'))['rules']
    register = (SPEC / 'DIRECTION_CHANGES.md').read_text(encoding='utf-8')
    for r in rules:
        assert r['id'].rstrip('ab') in register, r['id']
