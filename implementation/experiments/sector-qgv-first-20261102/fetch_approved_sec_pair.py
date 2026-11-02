"""Owner-approved two-source SEC read for CIK 2488; no retries or redirects.

The approval permits at most six successful GETs, but this first step requests
only the two fixed sources. The optional identity follow-up is the single 8-K
selected after reviewing the saved submissions metadata. Output is private and append-only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCES = (
    ('submission', 'https://www.sec.gov/Archives/edgar/data/2488/000000248817000227/0000002488-17-000227.txt'),
    ('history', 'https://data.sec.gov/submissions/CIK0000002488-submissions-001.json'),
)
IDENTITY_SOURCE = ('identity', 'https://www.sec.gov/Archives/edgar/data/2488/000000248818000014/0000002488-18-000014.txt')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def save(path, data):
    with path.open('xb') as f:
        f.write(data)
    path.chmod(0o600)


def run(out, identity_followup=False):
    out = out.resolve()
    if any((p / '.git').exists() for p in (out, *out.parents)):
        raise ValueError('PRIVATE_OUTPUT_REQUIRED')
    rows = []
    if identity_followup:
        previous = json.loads((out / 'request-summary.json').read_text())
        if previous['successful_gets'] != 2 or previous['attempted_gets'] != 2:
            raise ValueError('SUCCESSFUL_FIXED_PAIR_REQUIRED')
        rows = [json.loads((out / (k + '.receipt.json')).read_text()) for k, _ in SOURCES]
        sources = (IDENTITY_SOURCE,)
    else:
        if out.exists():
            raise ValueError('NEW_PRIVATE_OUTPUT_REQUIRED')
        out.mkdir(parents=True, mode=0o700)
        sources = SOURCES
    out.chmod(0o700)
    # Do not fabricate an email or impersonate a browser when no configured UA exists.
    agent = os.environ.get('SEC_USER_AGENT') or (
        'Investment-System1 Research/1.0 (https://github.com/kco994553-star/Investment-System1)')
    opener = build_opener(NoRedirect())  # retains runtime proxies and verified TLS
    errors = 0
    for key, url in sources:
        row = dict(source=key, url=url, method='GET', retry=False,
                   started_at=datetime.now(timezone.utc).isoformat(),
                   user_agent_source='SEC_USER_AGENT' if os.environ.get('SEC_USER_AGENT') else 'PROJECT_URL_CONTACT')
        # A started receipt exists even if execution is interrupted.
        save(out / (key + '.started.json'), json.dumps(row, indent=2).encode())
        body = b''
        try:
            with opener.open(Request(url, headers={'User-Agent': agent, 'Accept': '*/*'}), timeout=35) as r:
                row.update(http_status=r.status, content_type=r.headers.get('Content-Type'),
                           final_url=r.geturl())
                body = r.read()
                row['success'] = 200 <= r.status < 300
        except HTTPError as e:
            row.update(http_status=e.code, success=False, error='HTTP_ERROR',
                       content_type=e.headers.get('Content-Type'))
            body = e.read()
        except (URLError, TimeoutError, OSError) as e:
            row.update(http_status=None, success=False, error=type(e).__name__)
        row.update(finished_at=datetime.now(timezone.utc).isoformat(), bytes=len(body),
                   sha256=hashlib.sha256(body).hexdigest())
        save(out / (key + '.response'), body)
        save(out / (key + '.receipt.json'), (json.dumps(row, indent=2) + '\n').encode())
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ('source', 'http_status', 'success', 'error', 'bytes')}), flush=True)
        if not row['success']:
            errors += 1
        if errors >= 2:
            break
    summary = dict(approval_success_limit=6, attempted_gets=len(rows),
                   successful_gets=sum(r['success'] for r in rows), failed_gets=errors,
                   retries=0, redirects_followed=0, additional_filings_requested=int(identity_followup),
                   stop_reason='REPEATED_FAILURE_STOP' if errors >= 2 else 'REVIEWED_SCOPE_COMPLETE')
    name = 'request-summary-after-identity.json' if identity_followup else 'request-summary.json'
    save(out / name, (json.dumps(summary, indent=2) + '\n').encode())
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--identity-followup', action='store_true')
    args = parser.parse_args()
    run(args.out, args.identity_followup)
