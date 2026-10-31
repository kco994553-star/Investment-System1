"""ONE-TIME READ-ONLY KIS VERIFICATION (owner 2026-10-31). Not part of any pipeline; the branch is never merged.

Prints only: whether the two secrets are present (yes/no), per call the endpoint TR id, HTTP status, rt_cd, msg_cd,
row counts, whether the expected value field is present, date ranges, elapsed time, and public master-file row counts.
Never prints keys, the access token, prices or other values, response bodies or headers. Only the token issue/revoke
endpoints and quotation endpoints in ALLOWED are callable; order, account and balance endpoints are not.
Usage: python kis_readonly_verify.py   (env KIS_APP_KEY, KIS_APP_SECRET)"""
import io, json, os, sys, time, urllib.error, urllib.parse, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

BASES = {'REAL': 'https://openapi.koreainvestment.com:9443', 'PAPER': 'https://openapivts.koreainvestment.com:29443'}
ALLOWED = {
    '/oauth2/tokenP', '/oauth2/revokeP',
    '/uapi/domestic-stock/v1/quotations/inquire-price',
    '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice',
    '/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice',
    '/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice',
    '/uapi/domestic-stock/v1/quotations/intstock-multprice',
    '/uapi/overseas-price/v1/quotations/price',
    '/uapi/overseas-price/v1/quotations/dailyprice',
    '/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice',
}
MASTERS = ['kospi_code.mst.zip', 'kosdaq_code.mst.zip', 'konex_code.mst.zip',
           'nasmst.cod.zip', 'nysmst.cod.zip', 'amsmst.cod.zip', 'tsemst.cod.zip']
MASTER_BASE = 'https://new.real.download.dws.co.kr/common/master/'
KEY, SECRET = os.environ.get('KIS_APP_KEY', ''), os.environ.get('KIS_APP_SECRET', '')
STATE = {'base': None, 'token': None, 'env': None}


def out(*parts):
    print('KISV', *parts, flush=True)


def call(method, path, *, body=None, params=None, tr_id=None, auth=True):
    """One request. Returns (http_status, parsed_json_or_None, elapsed_ms). Never prints anything itself."""
    if path not in ALLOWED or any(w in path for w in ('order', 'trading', 'balance', 'account')):
        raise SystemExit('PATH_NOT_ALLOWED')
    url = STATE['base'] + path + ('?' + urllib.parse.urlencode(params) if params else '')
    headers = {'content-type': 'application/json; charset=utf-8'}
    if auth:
        headers.update({'authorization': 'Bearer ' + STATE['token'], 'appkey': KEY, 'appsecret': SECRET,
                        'tr_id': tr_id, 'custtype': 'P'})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            status, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception as e:  # network failure: report the class only
        return 'NET_' + type(e).__name__, None, int((time.monotonic() - t0) * 1000)
    ms = int((time.monotonic() - t0) * 1000)
    try:
        return status, json.loads(raw.decode('utf-8', 'replace')), ms
    except ValueError:
        return status, None, ms


def codes(j):
    if not isinstance(j, dict):
        return 'rt_cd=- msg_cd=-'
    return 'rt_cd=%s msg_cd=%s' % (j.get('rt_cd', '-'), j.get('msg_cd') or j.get('error_code') or '-')


def rows(j, key):
    v = j.get(key) if isinstance(j, dict) else None
    return len(v) if isinstance(v, list) else (1 if isinstance(v, dict) and v else 0)


def span(j, key, date_field):
    v = j.get(key) if isinstance(j, dict) else None
    ds = sorted(x.get(date_field) for x in v if isinstance(x, dict) and x.get(date_field)) if isinstance(v, list) else []
    return '%s..%s' % (ds[0], ds[-1]) if ds else '-'


def has(j, key, field):
    v = j.get(key) if isinstance(j, dict) else None
    if isinstance(v, list):
        v = v[0] if v else None
    return 'yes' if isinstance(v, dict) and str(v.get(field, '')).strip() not in ('', '0', '0.0', '0.0000') else 'no'


def token():
    for env in ('REAL', 'PAPER'):
        STATE['base'] = BASES[env]
        st, j, ms = call('POST', '/oauth2/tokenP', body={'grant_type': 'client_credentials', 'appkey': KEY, 'appsecret': SECRET}, auth=False)
        ok = isinstance(j, dict) and bool(j.get('access_token'))
        out('TOKEN', 'env=%s' % env, 'http=%s' % st, 'ok=%s' % ('yes' if ok else 'no'), codes(j),
            'expires_in=%s' % (j.get('expires_in') if ok else '-'), 'token_type=%s' % (j.get('token_type') if ok else '-'), 'ms=%s' % ms)
        if ok:
            STATE['token'], STATE['env'] = j['access_token'], env
            return True
        if env == 'REAL':
            time.sleep(65)  # issuance is limited to about once per minute
    return False


def main():
    out('SECRET_PRESENT', 'KIS_APP_KEY=%s' % ('yes' if KEY else 'no'), 'KIS_APP_SECRET=%s' % ('yes' if SECRET else 'no'))
    masters()
    if not (KEY and SECRET):
        out('STOP', 'secrets_missing')
        return
    if not token():
        out('STOP', 'auth_failed')
        return
    today = datetime.now(timezone(timedelta(hours=9))).strftime('%Y%m%d')
    start = (datetime.now(timezone.utc) - timedelta(days=200)).strftime('%Y%m%d')
    # domestic current price (3 symbols)
    for code in ('005930', '000660', '042700', '069500'):
        st, j, ms = call('GET', '/uapi/domestic-stock/v1/quotations/inquire-price', tr_id='FHKST01010100',
                         params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': code})
        out('DOM_PRICE', code, 'http=%s' % st, codes(j), 'value_field=%s' % has(j, 'output', 'stck_prpr'), 'ms=%s' % ms)
        time.sleep(0.2)
    # domestic daily bars (max rows per call)
    st, j, ms = call('GET', '/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice', tr_id='FHKST03010100',
                     params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': '005930', 'FID_INPUT_DATE_1': start,
                             'FID_INPUT_DATE_2': today, 'FID_PERIOD_DIV_CODE': 'D', 'FID_ORG_ADJ_PRC': '0'})
    out('DOM_DAILY', '005930', 'http=%s' % st, codes(j), 'rows=%s' % rows(j, 'output2'), 'dates=%s' % span(j, 'output2', 'stck_bsop_date'), 'ms=%s' % ms)
    time.sleep(0.2)
    # domestic intraday minute bars (today)
    st, j, ms = call('GET', '/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice', tr_id='FHKST03010200',
                     params={'FID_ETC_CLS_CODE': '', 'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': '005930',
                             'FID_INPUT_HOUR_1': '153000', 'FID_PW_DATA_INCU_YN': 'Y'})
    out('DOM_MINUTE_TODAY', '005930', 'http=%s' % st, codes(j), 'rows=%s' % rows(j, 'output2'), 'dates=%s' % span(j, 'output2', 'stck_bsop_date'), 'ms=%s' % ms)
    time.sleep(0.2)
    # domestic past-day minute bars (last weekday)
    last = datetime.now(timezone(timedelta(hours=9)))
    while True:
        last -= timedelta(days=1)
        if last.weekday() < 5:
            break
    st, j, ms = call('GET', '/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice', tr_id='FHKST03010230',
                     params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': '005930', 'FID_INPUT_HOUR_1': '153000',
                             'FID_INPUT_DATE_1': last.strftime('%Y%m%d'), 'FID_PW_DATA_INCU_YN': 'Y', 'FID_FAKE_TICK_INCU_YN': ''})
    out('DOM_MINUTE_PASTDAY', '005930', last.strftime('%Y%m%d'), 'http=%s' % st, codes(j), 'rows=%s' % rows(j, 'output2'),
        'dates=%s' % span(j, 'output2', 'stck_bsop_date'), 'ms=%s' % ms)
    time.sleep(0.2)
    # domestic multi-symbol price (up to 30 per call, if available to this account)
    params = {}
    for i, code in enumerate(('005930', '000660', '042700'), start=1):
        params['FID_COND_MRKT_DIV_CODE_%d' % i] = 'J'
        params['FID_INPUT_ISCD_%d' % i] = code
    st, j, ms = call('GET', '/uapi/domestic-stock/v1/quotations/intstock-multprice', tr_id='FHKST11300006', params=params)
    out('DOM_MULTI', 'n=3', 'http=%s' % st, codes(j), 'rows=%s' % rows(j, 'output'), 'ms=%s' % ms)
    time.sleep(0.2)
    # overseas current price (3 symbols, 3 exchanges)
    for excd, sym in (('NAS', 'AAPL'), ('NAS', 'NVDA'), ('NYS', 'IBM'), ('AMS', 'SPY'), ('TSE', '8035')):
        st, j, ms = call('GET', '/uapi/overseas-price/v1/quotations/price', tr_id='HHDFS00000300',
                         params={'AUTH': '', 'EXCD': excd, 'SYMB': sym})
        out('OVS_PRICE', excd, sym, 'http=%s' % st, codes(j), 'value_field=%s' % has(j, 'output', 'last'), 'ms=%s' % ms)
        time.sleep(0.2)
    st, j, ms = call('GET', '/uapi/overseas-price/v1/quotations/dailyprice', tr_id='HHDFS76240000',
                     params={'AUTH': '', 'EXCD': 'NAS', 'SYMB': 'AAPL', 'GUBN': '0', 'BYMD': '', 'MODP': '1'})
    out('OVS_DAILY', 'NAS', 'AAPL', 'http=%s' % st, codes(j), 'rows=%s' % rows(j, 'output2'), 'dates=%s' % span(j, 'output2', 'xymd'), 'ms=%s' % ms)
    time.sleep(0.2)
    st, j, ms = call('GET', '/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice', tr_id='HHDFS76950200',
                     params={'AUTH': '', 'EXCD': 'NAS', 'SYMB': 'AAPL', 'NMIN': '1', 'PINC': '1', 'NEXT': '', 'NREC': '120', 'FILL': '', 'KEYB': ''})
    out('OVS_MINUTE', 'NAS', 'AAPL', 'http=%s' % st, codes(j), 'rows=%s' % rows(j, 'output2'), 'dates=%s' % span(j, 'output2', 'xymd'), 'ms=%s' % ms)
    # rate behaviour: two short bursts on one quotation endpoint, counts only
    for label, n, gap in (('10ps', 20, 0.1), ('25ps', 30, 0.04)):
        ok = err = 0
        errs = {}
        t0 = time.monotonic()
        for _ in range(n):
            st, j, _ms = call('GET', '/uapi/domestic-stock/v1/quotations/inquire-price', tr_id='FHKST01010100',
                              params={'FID_COND_MRKT_DIV_CODE': 'J', 'FID_INPUT_ISCD': '005930'})
            if isinstance(j, dict) and j.get('rt_cd') == '0':
                ok += 1
            else:
                err += 1
                k = (j or {}).get('msg_cd', str(st)) if isinstance(j, dict) else str(st)
                errs[k] = errs.get(k, 0) + 1
            time.sleep(gap)
        out('RATE', label, 'calls=%d' % n, 'ok=%d' % ok, 'err=%d' % err, 'err_codes=%s' % json.dumps(errs, sort_keys=True),
            'seconds=%.1f' % (time.monotonic() - t0))
        time.sleep(2)
    st, j, ms = call('POST', '/oauth2/revokeP', body={'appkey': KEY, 'appsecret': SECRET, 'token': STATE['token']}, auth=False)
    out('REVOKE', 'http=%s' % st, codes(j), 'ms=%s' % ms)
    STATE['token'] = None
    out('DONE', 'env=%s' % STATE['env'])


def masters():
    """Public master files (no authentication): byte size and row count only."""
    for name in MASTERS:
        for attempt in (1, 2, 3):
            t0 = time.monotonic()
            try:
                with urllib.request.urlopen(MASTER_BASE + name, timeout=60) as r:
                    blob = r.read()
                z = zipfile.ZipFile(io.BytesIO(blob))
                n = sum(sum(1 for line in z.open(m) if line.strip()) for m in z.namelist())
                out('MASTER', name, 'bytes=%d' % len(blob), 'rows=%d' % n, 'attempt=%d' % attempt, 'ms=%d' % int((time.monotonic() - t0) * 1000))
                break
            except Exception as e:
                if attempt == 3:
                    out('MASTER', name, 'error=%s' % type(e).__name__)
                time.sleep(3)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        out('ERROR', type(e).__name__)  # class only: never the message, which could echo a request
        sys.exit(1)
