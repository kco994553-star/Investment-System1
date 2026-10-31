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
        '공개 TARGET은 카탈로그 19개(v0)로 한다.',
        'TARGET 19 = QGV가 고른 포트폴리오',
        'Public TARGET is the catalog 19.',
        # DC-31 (2026-10-31, device V abolished)
        '중앙 V가 늦으면 기기 V로 채운다.',
        '공식 V가 없으면 임시 V로 표시한다.',
        '게시 전에는 임시 V를 보여 준다.',
        'If the publication is stale, fall back to the device V.',
        'Use the device V as a fallback when the central file is missing.',
        '지금 화면의 V는 기기 V다.',
        'V is computed on this device from its prices.',
        'V는 이 기기의 가격으로 계산한다.',
        '기기에 V 이력을 저장해 20거래일 기울기를 만든다.',
        'Device V history is stored in localStorage.',
        '중앙 V가 STALE이면 기기 V를 보여 준다.',
        '공식 V가 없을 때는 기기에서 계산한 V를 쓴다.',
        'When the central V is missing, show the device V.',
        'If the publication is stale, the screen uses the device V.',
        'V 점수는 이 기기에서 계산한다.',
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
        'TARGET v0은 QGV와 전혀 무관하다(DC-24).',
        '공개 TARGET은 확정된 TARGET v1만이다.',
        'TARGET v0(19)은 사용자가 QGV 없이 고른 것',
        '공개 TARGET 카탈로그 형식 오류',
        # DC-31: sentences that describe the abolition pass
        '기기 V는 폐지했다(DC-31): 공식 V가 없으면 사유와 NA, 기기 값으로 채우지 않는다.',
        'Device V was abolished (DC-31); no fallback: stale central V is shown with STALE.',
        'TARGET v1 빌더는 11/16까지 PR-D 규칙(공식 V 우선, 없으면 임시 V)을 유지한다.',
        '중앙 V 게시가 늦으면 마지막 중앙 V와 갱신 시각을 보이고 STALE로 표시한다.',
        'V 이력이 필요하면 중앙에서 날짜별로 게시한다(DC-31).',
        'The radar V axis reads the central publication (qgv-official.json).',
        '기기 계산 V는 모두 중앙 V로 대체(GSQ-025)',
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
