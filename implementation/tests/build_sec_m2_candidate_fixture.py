"""Explicit browser-test fixture builder. Synthetic test vectors, never actual data."""
from pathlib import Path
from tempfile import TemporaryDirectory
import argparse
from tests.test_sec_m2_qg import retain, analyze
from investment_system.product.web_mvp import build


def build_fixture(out):
    out = Path(out)
    with TemporaryDirectory() as directory:
        root = Path(directory)
        candidate = analyze(root, [retain(root, 'asml'), retain(root, 'nvda'), retain(root, 'stry', metrics={})])
        candidate['candidate_data']['qgv']['data']['asml']['Q_score'] = 0
        for row in candidate['candidate_data']['leaderboard']['data']['rows']:
            if row['company_id'] == 'asml':
                row['Q_score'] = 0
        build(out / 'candidate', sec_m2_candidate=candidate)
        build(out / 'default')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    build_fixture(parser.parse_args().out)
