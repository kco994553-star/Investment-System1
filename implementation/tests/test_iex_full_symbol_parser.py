"""IEX full-symbol mode (`iex_last_trade --all-symbols`) and the unchanged Universe504 mode. SYNTHETIC data only.

The C parser (tools/iex_tops/iex_last_trade.c) is compiled into a temp dir and fed synthetic IEX-TP v1 / TOPS 1.6 captures
built here with the builders of tests/test_iex_hist.py. Every symbol, price and timestamp below is made up; nothing touches
the network.
"""
import gzip
import hashlib
import json
import shutil
import struct
import subprocess

import pytest

from tests.test_iex_hist import CANARY_E4, ROOT, _sym, pcap, status_msg, trade

T0, T1 = 1_800_000_000 * 10**9, 1_800_023_400 * 10**9     # a made-up 6.5 h session window
M = 60 * 10**9
BASE_COMMIT = 'cef0748ec56e6fafa59156540df81ae653f6281f'  # last commit of the parser before the full-symbol mode
PARSER_PATH = 'implementation/tools/iex_tops/iex_last_trade.c'


@pytest.fixture(scope='module')
def parser(tmp_path_factory):
    if not shutil.which('cc'):
        pytest.skip('no C compiler')
    out = tmp_path_factory.mktemp('parser') / 'iex_last_trade'
    subprocess.run(['cc', '-O2', '-o', str(out), str(ROOT / 'tools/iex_tops/iex_last_trade.c')], check=True)
    return str(out)


def directory_msg(sym, ts, flags=0, round_lot=100):
    return struct.pack('<BBq8sIqB', 0x44, flags, ts, _sym(sym), round_lot, 0, 1)


def status_reason(sym, ts, status, reason):
    return struct.pack('<Bcq8s4s', 0x48, status, ts, _sym(sym), reason)


def quote(sym, ts):
    return struct.pack('<BBq8sIqqI', 0x51, 0, ts, _sym(sym), 1, 2, 3, 4)


def trade_id(sym, ts, px_e4, tid, flags=0, size=100):
    return struct.pack('<BBq8sIqq', 0x54, flags, ts, _sym(sym), size, px_e4, tid)


def trade_break(sym, ts, px_e4, tid):
    return struct.pack('<BBq8sIqq', 0x42, 0, ts, _sym(sym), 100, px_e4, tid)


def seg_frame(messages, seq, proto=0x8003):
    """test_iex_hist.frame with a real first-message sequence number, so a clean capture has no sequence gap."""
    payload = b''.join(struct.pack('<H', len(m)) + m for m in messages)
    tp = struct.pack('<BBHIIHHqqq', 1, 0, proto, 1, 1, len(payload), len(messages), 0, seq, 0) + payload
    udp = struct.pack('>HHHH', 1, 2, 8 + len(tp), 0) + tp
    ip = bytes([0x45, 0]) + struct.pack('>H', 20 + len(udp)) + bytes(5) + bytes([17]) + bytes(10) + udp
    return bytes(12) + b'\x08\x00' + ip


def capture(groups, skip_seq=0):
    """groups: list of message lists, one frame each, sequence numbers contiguous (or with `skip_seq` missing at frame 1)."""
    frames, seq = [], 1
    for i, g in enumerate(groups):
        if i == 1:
            seq += skip_seq
        frames.append(seg_frame(g, seq))
        seq += len(g)
    return pcap(frames)


def pcapng(frames):
    out = struct.pack('<IIIHHq', 0x0A0D0D0A, 28, 0x1A2B3C4D, 1, 0, -1) + struct.pack('<I', 28)
    for f in frames:
        pad = f + bytes((-len(f)) % 4)
        tl = 32 + len(pad)
        out += struct.pack('<IIIIIII', 6, tl, 0, 0, 0, len(f), len(f)) + pad + struct.pack('<I', tl)
    return out


def run_all(parser, body, *extra, t0=T0, t1=T1):
    return subprocess.run([parser, '--all-symbols', str(t0), str(t1), *extra], input=body, capture_output=True)


def rows_of(p):
    assert p.returncode == 0, p.stderr
    assert p.stderr == b''                                   # values stay in the output stream only
    lines = [json.loads(x) for x in p.stdout.decode('ascii').splitlines()]
    assert [x['record'] for x in lines] == ['symbol'] * (len(lines) - 1) + ['summary']
    return {r['symbol']: r for r in lines[:-1]}, lines[-1], [r['symbol'] for r in lines[:-1]]


def chunks(msgs, n=1000):
    return [msgs[i:i + n] for i in range(0, len(msgs), n)]


# ---- full-symbol mode --------------------------------------------------------------------------------------------------
def test_more_than_1024_symbols_all_rows_sorted_and_summary(parser):
    names = [f'S{i:05d}' for i in range(3000)]
    msgs = []
    for i, s in enumerate(names):
        msgs += [directory_msg(s, T0 - 2 * M), status_msg(s, T0 - M)]
        if i % 3 == 0:
            msgs.append(trade_id(s, T0 + M + i, 100000 + i, i))
    body = capture(chunks(msgs))
    p = run_all(parser, body, '--source-bytes', '12345', '--source-sha256', 'AB' * 32)
    rows, summary, order = rows_of(p)
    assert len(rows) == 3000 and order == sorted(names)
    assert sum(r['last_round_trade'] is not None for r in rows.values()) == 1000
    assert rows['S00003']['last_round_trade'] == {'price_e4': 100003, 'size': 100, 'ts': T0 + M + 3, 'broken': False}
    assert summary['symbols'] == 3000 and summary['symbol_ceiling'] == 50000 and summary['mode'] == 'all_symbols'
    assert summary['parser'] == 'iex_last_trade' and summary['parser_version'] == '2026-11-05.1'
    assert (summary['symbols_with_directory'], summary['symbols_with_trading_status'], summary['symbols_with_round_trade']) == (3000, 3000, 1000)
    assert summary['stdin_bytes'] == len(body) and summary['stdin_sha256'] == hashlib.sha256(body).hexdigest()
    assert (summary['source_bytes'], summary['source_sha256']) == (12345, 'ab' * 32)
    assert summary['messages'] == len(msgs) and summary['segments'] == len(chunks(msgs))
    assert (summary['truncated'], summary['gaps_detected'], summary['symbol_ceiling_exceeded'], summary['complete']) == (False, False, False, True)
    assert (summary['session_start_ns'], summary['session_end_ns'], summary['capture_format']) == (T0, T1, 'pcap')


def test_directory_only_status_only_halted_and_no_trade_symbols_stay_rows(parser):
    body = capture([[directory_msg('DIRONLY', T0 - M, flags=0x80, round_lot=10)],
                    [status_msg('STATONLY', T0 - M)],
                    [directory_msg('HALTED', T0 - 3 * M), status_reason('HALTED', T0 - 2 * M, b'T', b'    '),
                     trade_id('HALTED', T0 + M, 2500000, 7), status_reason('HALTED', T0 + 2 * M, b'H', b'T1  ')],
                    [directory_msg('NOTRADE', T0 - M), status_msg('NOTRADE', T0 - M), quote('NOTRADE', T0 + M)],
                    [quote('QUOTONLY', T0 + M)]])
    rows, summary, _ = rows_of(run_all(parser, body))
    assert set(rows) == {'DIRONLY', 'STATONLY', 'HALTED', 'NOTRADE', 'QUOTONLY'}
    d = rows['DIRONLY']
    assert (d['directory_seen'], d['directory_ts'], d['directory_flags'], d['round_lot_size']) == (True, T0 - M, 0x80, 10)
    assert (d['trading_status_seen'], d['trading_status'], d['trading_status_ts'], d['last_round_trade']) == (False, None, None, None)
    s = rows['STATONLY']
    assert (s['directory_seen'], s['directory_ts'], s['trading_status_seen'], s['trading_status'], s['trading_status_ts']) == (False, None, True, 'T', T0 - M)
    h = rows['HALTED']                                      # the LAST status in stream order, with its own timestamp
    assert (h['trading_status'], h['trading_status_ts'], h['trading_status_reason'], h['status_messages']) == ('H', T0 + 2 * M, 'T1', 2)
    assert h['last_round_trade']['price_e4'] == 2500000      # the trade before the halt is still recorded, separately
    n = rows['NOTRADE']
    assert (n['last_round_trade'], n['trade_reports'], n['quote_updates']) == (None, 0, 1)
    assert rows['QUOTONLY']['directory_seen'] is False and rows['QUOTONLY']['trading_status_seen'] is False
    assert summary['symbols_directory_without_status'] == 1
    for r in rows.values():                                  # nothing here decides tradable / listed / eligible
        assert not {'tradable', 'listed', 'eligible', 'valid_from', 'valid_to'} & set(r)


def test_odd_lot_extended_and_outside_window_never_the_round_lot_last_trade(parser):
    body = capture([[trade_id('AAA', T0 + M, 1000000, 1), trade_id('AAA', T0 + 2 * M, CANARY_E4, 2),
                     trade_id('AAA', T0 + 3 * M, 999999, 3, flags=0x20),          # later odd lot: not the last round trade
                     trade_id('AAA', T1 + M, 888888, 4, flags=0x40),              # extended hours
                     trade_id('AAA', T0 - M, 777777, 5)],                         # before the window
                    [trade_id('ODD', T0 + M, 555555, 6, flags=0x20, size=7)],
                    [trade_id('EXT', T1 + M, 444444, 7, flags=0x40), trade_id('EXT', T1, 444444, 8)]])
    rows, _, _ = rows_of(run_all(parser, body))
    a = rows['AAA']
    assert a['last_round_trade'] == {'price_e4': CANARY_E4, 'size': 100, 'ts': T0 + 2 * M, 'broken': False}
    assert (a['trade_reports'], a['trades_regular_round'], a['trades_regular_odd'], a['trades_excluded']) == (5, 2, 1, 2)
    assert rows['ODD']['last_round_trade'] is None and rows['ODD']['trades_regular_odd'] == 1
    assert rows['EXT']['last_round_trade'] is None and rows['EXT']['trades_excluded'] == 2   # end of the window is exclusive


def test_trade_break_flags_only_the_broken_last_trade(parser):
    body = capture([[trade_id('BRK', T0 + M, 1000000, 11), trade_break('BRK', T0 + 2 * M, 1000000, 11)],
                    [trade_id('OLD', T0 + M, 1000000, 21), trade_id('OLD', T0 + 2 * M, 1100000, 22),
                     trade_break('OLD', T0 + 3 * M, 1000000, 21)]])
    rows, summary, _ = rows_of(run_all(parser, body))
    assert rows['BRK']['last_round_trade']['broken'] is True and rows['BRK']['trade_breaks'] == 1
    assert rows['OLD']['last_round_trade'] == {'price_e4': 1100000, 'size': 100, 'ts': T0 + 2 * M, 'broken': False}
    assert summary['trade_breaks'] == 2


def test_original_symbol_text_is_kept_and_escaped(parser):
    body = capture([[directory_msg('BRK.B', T0), directory_msg('A+', T0), directory_msg('ZIEXT', T0, flags=0x80)],
                    [struct.pack('<Bcq8s4s', 0x48, b'T', T0, b'Q"\\\x01    ', b'    ')]])
    p = run_all(parser, body)
    rows, _, order = rows_of(p)
    assert order == ['A+', 'BRK.B', 'Q"\\\x01', 'ZIEXT']
    assert b'"symbol":"Q\\"\\\\\\u0001"' in p.stdout


def test_symbol_ceiling_exceeded_is_a_named_failure_with_no_rows(parser):
    six = capture([[directory_msg(f'C{i}', T0) for i in range(6)]])
    p = run_all(parser, six, '--max-symbols', '5')
    assert (p.returncode, p.stdout) == (6, b'') and p.stderr.startswith(b'#ERROR SYMBOL_CEILING_EXCEEDED ceiling=5')
    rows, summary, _ = rows_of(run_all(parser, six, '--max-symbols', '6'))
    assert len(rows) == 6 and summary['symbol_ceiling'] == 6


def test_default_ceiling_is_50000_distinct_symbols(parser):
    msgs = [directory_msg(f'X{i:06d}', T0) for i in range(50000)]
    ok = run_all(parser, capture(chunks(msgs, 1500)))
    assert ok.returncode == 0 and ok.stdout.count(b'\n') == 50001 and b'"symbols":50000,' in ok.stdout
    over = run_all(parser, capture(chunks(msgs + [directory_msg('Y', T0)], 1500)))
    assert (over.returncode, over.stdout) == (6, b'') and b'SYMBOL_CEILING_EXCEEDED ceiling=50000' in over.stderr


def test_sequence_gap_truncation_and_pcapng(parser):
    groups = [[directory_msg('AAA', T0)], [status_msg('AAA', T0)], [trade_id('AAA', T0 + M, 1000000, 1)]]
    _, summary, _ = rows_of(run_all(parser, capture(groups, skip_seq=3)))
    assert (summary['sequence_gaps'], summary['sequence_gap_messages'], summary['gaps_detected'], summary['complete']) == (1, 3, True, False)
    assert summary['first_sequence'] == 1
    clean = capture(groups)
    cut = clean[:-5]
    rows, summary, _ = rows_of(run_all(parser, cut))
    assert (summary['truncated'], summary['complete'], summary['stdin_bytes']) == (True, False, len(cut))
    assert rows['AAA']['trading_status_seen'] is True                # rows before the cut are still written
    frames = [seg_frame(g, 1 + i) for i, g in enumerate(groups)]
    rows_ng, summary_ng, _ = rows_of(run_all(parser, pcapng(frames)))
    rows_pc, _, _ = rows_of(run_all(parser, clean))
    assert rows_ng == rows_pc and summary_ng['capture_format'] == 'pcapng' and summary_ng['complete'] is True


def test_stdin_hash_can_be_left_to_the_caller(parser):
    body = capture([[directory_msg('AAA', T0)]])
    rows, summary, _ = rows_of(run_all(parser, body, '--no-stdin-sha256', '--source-sha256', '0' * 64))
    assert (summary['stdin_sha256'], summary['source_sha256'], summary['stdin_bytes']) == (None, '0' * 64, len(body))
    assert rows == rows_of(run_all(parser, body))[0]


@pytest.mark.parametrize('args', [[], ['1'], ['2', '1'], ['x', '2'], ['1', '2', '--max-symbols', '0'], ['1', '2', '--max-symbols'],
                                  ['1', '2', '--source-sha256', 'zz'], ['1', '2', '--nope', '1']])
def test_bad_arguments_fail_closed(parser, args):
    p = subprocess.run([parser, '--all-symbols', *args], input=capture([[directory_msg('AAA', T0)]]), capture_output=True)
    assert (p.returncode, p.stdout, p.stderr) == (2, b'', b'#ERROR BAD_ARGUMENT\n')


def test_no_input_and_unknown_format_are_named(parser):
    assert run_all(parser, b'').returncode == 3 and b'NO_CAPTURE_HEADER' in run_all(parser, b'').stderr
    p = run_all(parser, b'\x00' * 64)
    assert (p.returncode, p.stdout) == (5, b'')


# ---- Universe504 mode: byte-identical to the parser before the full-symbol mode ---------------------------------------------
def legacy_fixture():
    """A fixed capture + symbols file exercising the 1024 cap, directory/status columns, odd/extended/window rules, DEEP and
    non-IEX segments, a malformed message and a cut tail. Deterministic arithmetic, no RNG."""
    names = [f'L{i:04d}' for i in range(1100)]
    msgs = []
    for i, s in enumerate(names):
        k = (i * 7919) % 11
        if k < 2:
            msgs.append(directory_msg(s, T0 - M))
        if k < 5:
            msgs.append(status_msg(s, T0 - M, status=b'THPO'[k % 4:k % 4 + 1]))
        if k in (3, 4, 5, 6):
            msgs.append(trade(s, T0 + (i % 97) * M, 100000 + i * 13, flags=(0, 0x20, 0x40, 0x80)[k - 3]))
        if k == 7:
            msgs += [trade(s, T0 + M, 200000 + i, flags=0x20), trade(s, T0 + 2 * M, 300000 + i)]
        if k == 8:
            msgs.append(trade(s, T1 + M, 400000 + i))
    frames = [seg_frame(c, 0, proto=(0x8003, 0x8004, 0x8003, 0x1234)[j % 4]) for j, c in enumerate(chunks(msgs, 200))]
    frames.append(seg_frame([b'\x54\x00'], 0))                         # a too-short trade message
    frames.append(b'\x00' * 30)                                          # a non-IP frame
    body = pcap(frames)[:-3]                                             # cut tail
    symbols = '\n'.join(names[::-1] + ['', 'TOOLONGSYM', 'L0001']) + '\n'
    return body, symbols


# SHA-256 of (stdout, stderr) of the pre-change parser (BASE_COMMIT) on legacy_fixture(), exit 0.
LEGACY_GOLDEN = ('9bab73c1710a6b890334eaec417c53ec58c8b687a8eac968b5ceabb87279df1c',
                 '3853fdb3d2fbbfaa89994e8dd8d5453821468adfa8f44a6c103219969f5ab65e')


def _legacy(parser, tmp_path, body, symbols):
    sf = tmp_path / 'symbols.txt'
    sf.write_text(symbols)
    return subprocess.run([parser, str(sf), str(T0), str(T1)], input=body, capture_output=True)


def test_universe504_mode_output_is_byte_identical_to_the_golden(parser, tmp_path):
    body, symbols = legacy_fixture()
    p = _legacy(parser, tmp_path, body, symbols)
    assert p.returncode == 0
    assert (hashlib.sha256(p.stdout).hexdigest(), hashlib.sha256(p.stderr).hexdigest()) == LEGACY_GOLDEN
    assert p.stdout.count(b'\n') == 1024                                 # the Universe504 cap is unchanged
    assert b'"record"' not in p.stdout


def test_universe504_mode_matches_the_pre_change_parser_source(parser, tmp_path):
    """When git can show the parser before this change, compile it and compare on several captures (also pcap-ng, gzip-free)."""
    git = shutil.which('git')
    old = subprocess.run([git, 'show', f'{BASE_COMMIT}:{PARSER_PATH}'], cwd=ROOT, capture_output=True) if git else None
    if not old or old.returncode != 0:
        pytest.skip('pre-change parser source not in this checkout (shallow clone)')
    src = tmp_path / 'old_parser.c'
    src.write_bytes(old.stdout)
    exe = tmp_path / 'old_parser'
    subprocess.run(['cc', '-O2', '-o', str(exe), str(src)], check=True)
    src.unlink()                                                         # keep exactly one .c file in the tree
    body, symbols = legacy_fixture()
    groups = [[status_msg('AAA', T0 - M), trade('AAA', T0 + M, 1000000)], [trade('AAA', T0 + 2 * M, CANARY_E4)],
              [trade('BBB', T0 + M, 555555, flags=0x20)], [directory_msg('CCC', T0)]]
    cases = [(body, symbols), (capture(groups), 'AAA\nBBB\nCCC\nDDD\n'),
             (pcapng([seg_frame(g, 0) for g in groups]), 'AAA\nCCC\n'), (b'', 'AAA\n'), (b'\x00' * 64, 'AAA\n'),
             (gzip.decompress(gzip.compress(capture(groups)))[:-9], 'BBB\nAAA\n')]
    for b, s in cases:
        a, n = _legacy(str(exe), tmp_path, b, s), _legacy(parser, tmp_path, b, s)
        assert (a.returncode, a.stdout, a.stderr) == (n.returncode, n.stdout, n.stderr)
    for args in ([], ['x'], ['a', 'b', 'c', 'd']):
        a = subprocess.run([str(exe), *args], input=b'', capture_output=True)
        n = subprocess.run([parser, *args], input=b'', capture_output=True)
        assert (a.returncode, a.stdout, a.stderr) == (n.returncode, n.stdout, n.stderr)
