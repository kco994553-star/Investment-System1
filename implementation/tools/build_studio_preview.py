"""Export a self-contained, explicitly synthetic HTML for local review only.

Not part of the public cockpit build. QGV profiles are precomputed by Python;
the interactive compounding port is regression-checked against SimulationEngine.
"""
import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from investment_system.product.studio import ASSETS, studio_snapshot


def build_preview(out):
    html = (ASSETS / 'index.html').read_text(encoding='utf-8')
    snapshots = {preset: studio_snapshot(preset) for preset in ('balanced', 'quality', 'growth', 'value')}
    data = json.dumps(snapshots, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    css = (ASSETS / 'studio.css').read_text(encoding='utf-8')
    runtime = (ASSETS / 'preview-runtime.js').read_text(encoding='utf-8')
    app = (ASSETS / 'studio.js').read_text(encoding='utf-8')
    html = re.sub(r'<link\s+rel="stylesheet"\s+href="/studio.css"\s*/?>', lambda _: '<style>' + css + '</style>', html)
    html = re.sub(r'<script\s+defer\s+src="/studio.js"\s*></script>', '', html)
    scripts = '<script>globalThis.__STUDIO_SNAPSHOTS__=' + data + ';</script><script>' + runtime + '</script><script>' + app + '</script>'
    html = html.replace('</body>', scripts + '</body>')
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    build_preview(args.out)
    print('Standalone DEMO preview exported')
