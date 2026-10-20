"""Export public cockpit metadata for Pages; never accept holdings or demo input."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
# Sibling pipeline tools (public_screens_pipeline, universe_domains_pipeline) also when loaded by file path.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent))
from investment_system.product.web_mvp import build, repository_bundle


def build_public_cockpit(out: Path, *, sec_m2_candidate=None) -> Path:
    out = Path(out)
    if out.is_symlink() or (out.exists() and (not out.is_dir() or any(out.iterdir()))):
        raise ValueError('Pages output must be an empty regular directory')
    bundle = repository_bundle()
    result = build(out, bundle=bundle, sec_m2_candidate=sec_m2_candidate)
    assets = Path(__file__).resolve().parents[1] / 'src/investment_system/product/web_assets'
    # Licence texts for the vendored chart renderer (lightweight-charts 5.2.1), pinned by the guard.
    for name in ('manifest.json', 'icon-192.png', 'icon-512.png', 'lightweight-charts-5.2.1.LICENSE.txt',
                 'lightweight-charts-5.2.1.NOTICE.txt', 'third-party-notices.txt'):
        shutil.copyfile(assets / name, out / name)
    # Price-free Universe504 code list for the Google sheet Universe tab (validated by the guard).
    from investment_system.universe.universe_codes import FILENAME as UNIVERSE_CODES, public_payload
    (out / UNIVERSE_CODES).write_text(json.dumps(public_payload(), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    # Reviewed Korean company-name table (KR-NAMES): display and search only, validated by the guard against the reviewed file.
    from investment_system.universe.company_names_ko import FILENAME as COMPANY_NAMES, public_payload as names_payload
    (out / COMPANY_NAMES).write_text(json.dumps(names_payload(), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    # Company domains and local PNG logo bundle; the browser never contacts logo providers.
    from universe_domains_pipeline import emit as emit_domains
    emit_domains(out)
    from company_logos_pipeline import emit as emit_logos
    emit_logos(out)
    from public_screens_pipeline import emit
    emit(out)
    from public_classification_pipeline import emit as emit_classification
    emit_classification(out)
    from dart_daily import emit as emit_dart
    emit_dart(out)
    from sec_disclosures import emit_empty as emit_disclosures
    emit_disclosures(out)
    from news_signals import emit_empty as emit_news
    emit_news(out)
    from macro_evidence import emit_empty as emit_macro_evidence
    emit_macro_evidence(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--sec-m2-candidate', help='Explicit private M2 JSON, projected into price-free research candidates')
    args = parser.parse_args()
    try:
        from investment_system.product.sec_m2_candidates import load_candidates
        candidate = load_candidates(args.sec_m2_candidate) if args.sec_m2_candidate else None
        build_public_cockpit(Path(args.out), sec_m2_candidate=candidate)
    except (OSError, ValueError):
        print('Pages public build failed', file=sys.stderr)
        return 1
    print('Pages public cockpit built')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
