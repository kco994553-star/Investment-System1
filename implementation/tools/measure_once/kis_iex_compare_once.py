"""ONE-TIME KIS vs IEX comparison (owner 2026-10-31, last KIS run; the branch is never merged).

Same run: (1) KIS auth check (token issue + revoke only), (2) for a fixed sample of 100 expansion candidates (25 per SEC
public-float bucket, chosen offline by sha256 order, symbols only), compare the IEX HIST last regular-session round-lot trade
(investment_system.providers.iex_hist.fetch_day; look back up to 4 earlier IEX days when the basis day has none) with the KIS
daily close (HHDFS76240000) of the same New York trading day. Prices stay in RAM; only aggregate lines are printed:
per bucket n, median / p90 of |diff| %, signed median %, count over 1 %, the IEX last-trade age distribution, and KIS error
code counts. Never prints a key, token, price, per-symbol value or response body; order/account endpoints are not callable."""
import datetime as dt, json, os, signal, statistics, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, 'implementation/src')
from investment_system.providers import iex_hist  # noqa: E402

SAMPLE = [["HTB", "NYS", "B1"], ["CMP", "NYS", "B1"], ["HLF", "NYS", "B1"], ["FTRE", "NAS", "B1"], ["SHLS", "NAS", "B1"], ["SITC", "NYS", "B1"], ["BOW", "NYS", "B1"], ["NPKI", "NYS", "B1"], ["ECVT", "NYS", "B1"], ["NXDR", "NAS", "B1"], ["FLOC", "NYS", "B1"], ["CCBG", "NAS", "B1"], ["CASS", "NAS", "B1"], ["WNC", "NYS", "B1"], ["PSBD", "NYS", "B1"], ["GHI", "NYS", "B1"], ["VIR", "NAS", "B1"], ["NGVC", "NYS", "B1"], ["HGTY", "NYS", "B1"], ["UAN", "NYS", "B1"], ["MLYS", "NAS", "B1"], ["BCAL", "NAS", "B1"], ["CABO", "NYS", "B1"], ["GDOT", "NYS", "B1"], ["APPS", "NAS", "B1"], ["AMC", "NYS", "B2"], ["LOB", "NYS", "B2"], ["UCTT", "NAS", "B2"], ["LUNR", "NAS", "B2"], ["BUSE", "NAS", "B2"], ["LCII", "NYS", "B2"], ["SABR", "NAS", "B2"], ["FIVN", "NAS", "B2"], ["ARCB", "NAS", "B2"], ["HLIO", "NYS", "B2"], ["PRVA", "NAS", "B2"], ["DXPE", "NAS", "B2"], ["HMN", "NYS", "B2"], ["WT", "NYS", "B2"], ["BELFB", "NAS", "B2"], ["TDOC", "NYS", "B2"], ["EOSE", "NAS", "B2"], ["PEB", "NYS", "B2"], ["CRTO", "NAS", "B2"], ["VICR", "NAS", "B2"], ["XHR", "NYS", "B2"], ["UPBD", "NAS", "B2"], ["LPG", "NYS", "B2"], ["AI", "NYS", "B2"], ["TPB", "NYS", "B2"], ["ABG", "NYS", "B3"], ["TREX", "NYS", "B3"], ["PAGP", "NAS", "B3"], ["CQP", "NYS", "B3"], ["HRB", "NYS", "B3"], ["CDE", "NYS", "B3"], ["APA", "NAS", "B3"], ["NCNO", "NAS", "B3"], ["BANR", "NAS", "B3"], ["VCTR", "NAS", "B3"], ["QS", "NAS", "B3"], ["DOCS", "NYS", "B3"], ["CBZ", "NYS", "B3"], ["ITRI", "NAS", "B3"], ["AYI", "NYS", "B3"], ["IRT", "NYS", "B3"], ["MSA", "NYS", "B3"], ["SAIA", "NAS", "B3"], ["TBBK", "NAS", "B3"], ["EXPO", "NAS", "B3"], ["ALV", "NYS", "B3"], ["EXP", "NYS", "B3"], ["BATRA", "NAS", "B3"], ["CUBE", "NYS", "B3"], ["BDC", "NYS", "B3"], ["ODFL", "NAS", "B4"], ["BNY", "NYS", "B4"], ["VRTX", "NAS", "B4"], ["QSR", "NYS", "B4"], ["WST", "NYS", "B4"], ["RJF", "NYS", "B4"], ["AEP", "NAS", "B4"], ["CNC", "NYS", "B4"], ["PSX", "NYS", "B4"], ["LYV", "NYS", "B4"], ["CW", "NYS", "B4"], ["BRO", "NYS", "B4"], ["SW", "NYS", "B4"], ["FTV", "NYS", "B4"], ["CHRW", "NAS", "B4"], ["HLI", "NYS", "B4"], ["SYY", "NYS", "B4"], ["FLEX", "NAS", "B4"], ["HAS", "NAS", "B4"], ["EXPD", "NYS", "B4"], ["DRI", "NYS", "B4"], ["PGR", "NYS", "B4"], ["WAB", "NYS", "B4"], ["TOST", "NYS", "B4"], ["CPNG", "NYS", "B4"]]
BASIS = dt.date(2026, 10, 29)
LOOKBACK_DAYS = 4
BASE = 'https://openapi.koreainvestment.com:9443'
ALLOWED = {'/oauth2/tokenP', '/oauth2/revokeP', '/uapi/overseas-price/v1/quotations/dailyprice'}
KEY, SECRET = os.environ.get('KIS_APP_KEY', ''), os.environ.get('KIS_APP_SECRET', '')
os.environ.pop('KIS_APP_KEY', None)      # no child process (curl, gzip, parser) inherits the secrets
os.environ.pop('KIS_APP_SECRET', None)
START = time.monotonic()
BUDGET_S = 50 * 60          # the step's `timeout 55m` minus a margin
KIS_RESERVE_S = 8 * 60      # token + 100 paced daily-bar calls + revoke
STREAM_EST_S = 12 * 60      # one IEX day stream (about 9-10 min measured locally)
MIN_SAME_DAY = 90           # no token unless at least this many symbols have a basis-day IEX trade


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):   # never forward the secret headers to another location
        return None


OPENER = urllib.request.build_opener(_NoRedirect)


def left():
    return BUDGET_S - (time.monotonic() - START)


def out(*parts):
    print('KISCMP', *parts, flush=True)


def call(method, path, *, token=None, body=None, params=None, tr_id=None):
    if path not in ALLOWED or any(w in path for w in ('order', 'trading', 'balance', 'account')):
        raise SystemExit('PATH_NOT_ALLOWED')
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    headers = {'content-type': 'application/json; charset=utf-8'}
    if token:
        headers.update({'authorization': 'Bearer ' + token, 'appkey': KEY, 'appsecret': SECRET, 'tr_id': tr_id, 'custtype': 'P'})
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
    try:
        with OPENER.open(req, timeout=20) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:
        return 'NET_' + type(e).__name__, None
    try:
        return status, json.loads(raw.decode('utf-8', 'replace'))
    except ValueError:
        return status, None


def _stream(link, day, symbols, parser, workdir):
    """curl | gzip -dc | iex_last_trade for one TOPS 1.6 day -> {SYM: (status, price_e4)} in RAM. A measurement-only fetch
    (like the 10/30 IEX census): public_price_boundary.require_price_route admits the publisher entry script only, and this
    branch does not change that guard. Parser stdout is read into memory and never written or printed."""
    workdir.mkdir(parents=True, exist_ok=True)
    symfile = workdir / ('kiscmp-symbols-%s.txt' % day)
    symfile.write_text('\n'.join(sorted(symbols)) + '\n', encoding='ascii')   # public tickers only
    t0, t1 = iex_hist.session_ns(day)
    max_time = str(max(60, int(left() - KIS_RESERVE_S)))
    p1 = subprocess.Popen(['curl', '-sS', '--fail', '--connect-timeout', '30', '--speed-limit', '1048576', '--speed-time', '60',
                           '--max-time', max_time, '-o', '-', link],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p2 = subprocess.Popen(['gzip', '-dc'], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p1.stdout.close()
    p3 = subprocess.Popen([parser, str(symfile), str(t0), str(t1)], stdin=p2.stdout, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL)
    p2.stdout.close()
    raw = p3.stdout.read()
    codes = (p1.wait(), p2.wait(), p3.wait())
    symfile.unlink(missing_ok=True)
    if codes != (0, 0, 0):
        raise RuntimeError('STREAM_EXIT_%d_%d_%d' % codes)
    return iex_hist.parse_rows(raw.decode('ascii', 'replace'), symbols)


def iex_phase(parser, workdir):
    """{symbol: (price, age_in_iex_days)} in RAM; age 0 = the basis IEX day (status ROUND = the central-V price definition).
    The basis day gets one fresh-pipeline retry; an older day is streamed only while one more stream still leaves the KIS
    reserve inside the budget. Returns (found, basis_day, basis_ok)."""
    with OPENER.open(iex_hist.HIST_URL, timeout=120) as r:
        index = json.load(r)
    files = iex_hist.tops_files(index)
    days = sorted(d for d in files if d <= BASIS.strftime('%Y%m%d'))[-(LOOKBACK_DAYS + 1):][::-1]
    found, todo, basis_ok = {}, {s for s, _, _ in SAMPLE}, False
    for age, day in enumerate(days):
        if not todo:
            break
        if age and left() < STREAM_EST_S + KIS_RESERVE_S:
            out('IEX_DAY', day, 'age=%d' % age, 'skipped=budget', 'left_s=%d' % int(left()))
            break
        rows = None
        for attempt in ((0, 1) if age == 0 else (0,)):
            t0 = time.monotonic()
            try:
                rows = _stream(files[day]['link'], day, todo, parser, workdir)
                break
            except Exception as e:
                out('IEX_DAY', day, 'age=%d' % age, 'attempt=%d' % attempt, 'seconds=%d' % int(time.monotonic() - t0),
                    'error=%s' % (str(e) if str(e).startswith('STREAM_EXIT_') or isinstance(e, iex_hist.IexHistError) else type(e).__name__))
                if attempt == 0 and age == 0 and left() > STREAM_EST_S + KIS_RESERVE_S:
                    time.sleep(15)
                else:
                    break
        if rows is None:
            if age == 0:
                break            # no basis day: the caller stops before any KIS call
            continue
        basis_ok = basis_ok or age == 0
        counts, hit = {}, 0
        for s in sorted(todo):
            st, px = rows.get(s, ('MISSING', None))
            counts[st] = counts.get(st, 0) + 1
            if st == 'ROUND' and px:
                found[s] = (px / 10000, age)
                todo.discard(s)
                hit += 1
        out('IEX_DAY', day, 'age=%d' % age, 'round=%d' % hit, 'status=%s' % json.dumps(counts, sort_keys=True),
            'seconds=%d' % int(time.monotonic() - t0))
        del rows
    return found, days[0] if days else None, basis_ok


def token():
    st, j = call('POST', '/oauth2/tokenP', body={'grant_type': 'client_credentials', 'appkey': KEY, 'appsecret': SECRET})
    ok = isinstance(j, dict) and bool(j.get('access_token'))
    out('TOKEN', 'http=%s' % st, 'ok=%s' % ('yes' if ok else 'no'), 'expires_in=%s' % (j.get('expires_in') if ok else '-'),
        'error_code=%s' % ((j or {}).get('error_code', '-') if not ok and isinstance(j, dict) else '-'))
    return j['access_token'] if ok else None


def kis_closes(tok, day):
    closes, fails = {}, {}
    retried = net_streak = 0
    for i, (sym, excd, _) in enumerate(SAMPLE):
        if left() < 60 or net_streak >= 5:   # leave time for the summary and the revoke
            fails['not_called_' + ('budget' if left() < 60 else 'net_streak')] = len(SAMPLE) - i
            break
        for attempt in (0, 1):   # one retry on the per-second limit / gateway routing codes (new keys: 3 calls/s for 3 days)
            st, j = call('GET', '/uapi/overseas-price/v1/quotations/dailyprice', token=tok, tr_id='HHDFS76240000',
                         params={'AUTH': '', 'EXCD': excd, 'SYMB': sym, 'GUBN': '0', 'BYMD': '', 'MODP': '0'})
            if attempt or not (isinstance(j, dict) and j.get('msg_cd') in ('EGW00201', 'EGW00300')):
                break
            retried += 1
            time.sleep(1.5)
        net_streak = net_streak + 1 if str(st).startswith('NET_') else 0
        rows = j.get('output2') if isinstance(j, dict) and j.get('rt_cd') == '0' else None
        row = next((r for r in rows if isinstance(r, dict) and r.get('xymd') == day), None) if isinstance(rows, list) else None
        try:
            c = float(row['clos']) if row else 0.0
        except (TypeError, ValueError, KeyError):
            c = 0.0
        if c > 0:
            closes[sym] = c
        else:
            if isinstance(j, dict) and j.get('rt_cd') != '0':
                k = str(j.get('msg_cd') or j.get('error_code') or st)
            else:
                k = 'NO_ROW_FOR_DAY' if rows is not None else str(st)
            fails[k] = fails.get(k, 0) + 1
        time.sleep(0.4)
    fails['retried'] = retried
    return closes, fails


MIN_N_STAT = 5   # an order statistic of fewer pairs would be close to one symbol's value: print '-'


def pct(values, q):
    if len(values) < MIN_N_STAT:
        return '-'
    s = sorted(values)
    return '%.3f' % s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def summary(found, closes):
    """Main figures on same-day pairs (IEX last trade on the basis day vs the KIS close of that day); pairs whose last IEX
    trade is older (age >= 1, never used by the central V, which leaves them NA) are counted apart."""
    buckets = {}
    for sym, _, b in SAMPLE:
        buckets.setdefault(b, []).append(sym)
    buckets['ALL'] = [s for s, _, _ in SAMPLE]
    for b, syms in buckets.items():
        abs_d, sgn, old_d, ages = [], [], [], {'d0': 0, 'd1': 0, 'd2': 0, 'd3_4': 0, 'none': 0}
        for s in syms:
            f = found.get(s)
            if f is None:
                ages['none'] += 1
            else:
                ages['d0' if f[1] == 0 else 'd1' if f[1] == 1 else 'd2' if f[1] == 2 else 'd3_4'] += 1
            if f is not None and s in closes:
                d = (f[0] - closes[s]) / closes[s] * 100
                if f[1] == 0:
                    abs_d.append(abs(d)); sgn.append(d)
                else:
                    old_d.append(abs(d))
        med = lambda v: '%.3f' % statistics.median(v) if len(v) >= MIN_N_STAT else '-'
        out('BUCKET', b, 'n_sample=%d' % len(syms), 'n_same_day=%d' % len(abs_d), 'median_abs_pct=%s' % med(abs_d),
            'p90_abs_pct=%s' % pct(abs_d, 0.9), 'signed_median_pct=%s' % med(sgn),
            'over_0_1pct=%d' % sum(1 for x in abs_d if x > 0.1), 'over_1pct=%d' % sum(1 for x in abs_d if x > 1.0),
            'over_5pct=%d' % sum(1 for x in abs_d if x > 5.0), 'n_older=%d' % len(old_d), 'older_median_abs_pct=%s' % med(old_d),
            'iex_age=%s' % json.dumps(ages, sort_keys=True))


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))   # a step timeout unwinds through `finally` (token revoke)
    out('SECRET_PRESENT', 'KIS_APP_KEY=%s' % ('yes' if KEY else 'no'), 'KIS_APP_SECRET=%s' % ('yes' if SECRET else 'no'),
        'sample=%d' % len(SAMPLE), 'basis=%s' % BASIS.isoformat())
    parser = os.environ.get('IEX_PARSER', '')
    workdir = Path(os.environ.get('IEX_WORKDIR', '/tmp'))
    found, day, basis_ok = {}, None, False
    try:
        found, day, basis_ok = iex_phase(parser, workdir)
    except Exception as e:
        out('IEX_PHASE', 'error=%s' % type(e).__name__)
    same_day = sum(1 for f in found.values() if f[1] == 0)
    out('IEX_FOUND', 'with_trade=%d' % len(found), 'same_day=%d' % same_day, 'of=%d' % len(SAMPLE), 'basis_day=%s' % day,
        'basis_ok=%s' % ('yes' if basis_ok else 'no'), 'left_s=%d' % int(left()))
    if not (KEY and SECRET):
        out('STOP', 'secrets_missing')
        summary(found, {})
        return
    if not basis_ok or same_day < MIN_SAME_DAY or day != BASIS.strftime('%Y%m%d'):
        out('STOP', 'iex_basis_failed', 'no_token_issued')   # the keyed run is not spent on a comparison without its basis day
        sys.exit(2)
    tok = None
    try:
        tok = token()
        if not tok:
            out('STOP', 'auth_failed')
            summary(found, {})
            return
        closes, fails = kis_closes(tok, day)
        summary(found, closes)
        out('KIS', 'closes=%d' % len(closes), 'fail_codes=%s' % json.dumps(fails, sort_keys=True))
    finally:
        if tok:
            st, j = call('POST', '/oauth2/revokeP', body={'appkey': KEY, 'appsecret': SECRET, 'token': tok})
            out('REVOKE', 'http=%s' % st)
        tok = None
        found.clear()
    out('DONE')


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        out('ERROR', type(e).__name__)
        sys.exit(1)
