"""Fail closed on the GSQ-010 price-free public Pages artifact.

Byte/canonical hashes protect reviewed assets. The independent public bundle
contract rejects legacy ranks, membership order, prices and arbitrary nested
values even if a legacy or modified payload hash is repinned. Private device
quotation code is an asset, never permission to publish device data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import tarfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from investment_system.public_price_boundary import require_public_bundle, require_public_catalog, PublicPriceBoundaryError


from investment_system.product.sec_m2_candidates import require_public_candidates
from investment_system.product.dart_public import FILENAMES as DART_FILENAMES, require_public as require_dart_public
from investment_system.product.news_signals import FILENAME as NEWS_SIGNALS_FILENAME, require_news_signals
from investment_system.product.sec_disclosures import FILENAME as DISCLOSURES_FILENAME, require_sec_disclosures
from investment_system.universe.sec_qgv2 import FILENAME as QGV2_FILENAME, require_qgv2
sys.path.insert(0, str(Path(__file__).resolve().parent))
from public_sec_inputs import FILENAME as SEC_PUBLIC_FILENAME, require_public_inputs
from investment_system.product.public_engine_screens import FILENAMES as SCREEN_FILENAMES, require_public_screen
from investment_system.universe.sec_universe_shares import FILENAME as UNIVERSE_SHARES_FILENAME, require_universe_shares
from investment_system.universe.sec_universe_qg import FILENAME as UNIVERSE_QG_FILENAME, require_universe_qg
from investment_system.validation.forward_ledger import FILENAME as FORWARD_LEDGER_FILENAME, require_ledger as require_forward_ledger
from investment_system.product.public_classification import FILENAME as CLASSIFICATION_FILENAME, require_public_classification
from investment_system.universe.universe_codes import FILENAME as UNIVERSE_CODES_FILENAME, require_universe_codes
from investment_system.universe.company_names_ko import FILENAME as COMPANY_NAMES_FILENAME, require_company_names_ko
from investment_system.universe.universe_domains import FILENAME as UNIVERSE_DOMAINS_FILENAME, require_universe_domains
from investment_system.product.company_logos import FILENAME as COMPANY_LOGOS_FILENAME, require_company_logos

# Reviewed public output, not hashes derived from potentially changed inputs.
APPROVED_SHA256 = {
    "playbook-engine.js": "b708a1772b4cd8e1af731cffdacbfab478d03c9c4e1e5fd663537babd64ee7d8",
    "playbook-config-defaults.js": "6a911d814782bcfb0aab098e9a05d0a5be494edc0026e08c8a0d124e3f2b00c2",
    "virtual-trading-compare.js": "700054fd105b979b505c09ec0dad862b0ce435c0179d2ddbe9f85b5b9c23c3f7",
    "tradingview-widgets.js": "e78e43406d480bb743b5c23aacb99435c3470c0e709ac1e3fcc2cec805366efc",
    "company-logos.js": "63aceb4033f17bba403f62b6c4887a8a9c5dd64b8a6f8180b063ab704ce38581",
    "report-benchmarks.js": "7a274ba8467880791df30deb17145396111e38c2d2598f7c654a0564c00aa6e9",
    "virtual-trading-runner.js": "3ae69b2b8920dbe539009968dd96aeb4248cf9f159a71fd4e6bb1398c9041827",
    "virtual-ledger-sheets.js": "4fda9c5505c6525b92a9b60ec170a9412abdcae4644ef83cbca59c270e03e4ec",
    "thirteenf-quarter.js": "0f95d210026f41c14c18ceb833a7df32cfa0e35604643b37cb0c5c1bc3c50b49",
    "worker-quote-fallback.js": "e72a72d1885a23c2a35706c8d4f333060b0c451d32a00e501dc63a30416b754c",
    "holdings-capture-view.js": "5f9b2952792c403ea3d005809508381432e17d0f588cfc5930f74413b1a5ba94",
    "holdings-capture.js": "a0fbd647c36d4714e743badbf445e2d3bf6b47c504766beaa14a93fdbf900d95",
    "table-sort.js": "db8ebe8e6a81a67309e925646ffe557db06452fb89e5735de7baad9770c0b778",
    "pc-layout.css": "d3a270238df767d49ef23ea3d53d60fca62d65dc017af19338269602190af2b4",
    "share-class-groups.js": "088bbfaec559937753533572330a6be3c2f9280910f9f6cf62b53f39119c0997",
    "forward-validation.js": "da7345bf97393f8cf986fd97f09b8044bc6d2f7051fff9020a00005239ad6dd3",
    "daily-report.js": "3d13a6e26992bda32e1a136f34895490941fba104a6ed4e09a285fc7ef22ca5a",
    "sec-universe-shares.js": "7a64bf6c280b81258ebd13e78b6761876f7056565f18ba9e64da897d953f600d",
    "virtual-trading-v-history.js": "944124763c2682dff373f9ec86e8b938ee2400f3084b5e3d62d8b44c8bd8099f",
    "virtual-trading-signals.js": "b8d73d216d9697bea31f15f0061831f81a144b518b5aa5cc54ba4620dafbe6ef",
    "sec-universe-qg.js": "92664e67228854456739880f2314b77da73155227995065e63d9711207fa3a2c",
    "sec-qgv2.js": "419b49c42921b2792a18ff051e3864620cfacec3918b3b98e74adf90d61cb48d",
    "device-valuation.js": "06669cda863cd4dfa87108f54e03b75c9321989967da7ed54b03c921143cfedf",
    "dcf-parameters-defaults.js": "3f9498ef6177b9dcd3c4fa80077c8480750be93668f57bd5ed5ed3b5509a8473",
    "classification-screens.js": "23ed7302742bf769068ef128dc48075fe6c88d6610585356e6b4e88d14db0a8f",
    "manager-styles-v0.js": "b32f434b17ba00d6ec1e4813517884e5caded996779df9b1976dfc38964ab38e",
    "screen-detail.js": "fdb5bb47c1a9b59ce1840640bc1a7f4bff69914a4d2985acc31dc0518d21af9c",
    "virtual-trading.js": "41a834f13d86ed2bd6a046cf63788992350294714ee9b9ee159ae50de8e20206",
    "technical-cards.js": "42bb2d1e8de0997eb8e7a2a3a25441d2ac29b010fb58b5fff1d879ba5eb03aad",
    "leaderboard-screen.js": "0c479d0bd7c1f3f71cbf4a0dd05a473625d551368a54edcd14e9db951c468474",
    "portfolio-screen.js": "5fdeea24f9d144e706226b687e9279bef141671d5987c194e4bb647db2fa2e69",
    "company-screen.js": "34c29f613d4defef20ffafc16e7651a08bd456f825b113a136f1a43611c82ee9",
    "ops-status.js": "bccccba913e0887ee2bb3c38fd61f27fcc2a6d37acb67aeeffea227df422c7a9",
    "type-config-defaults.js": "8b287dde54fb194469bd13d62c356e51eb78c4c04c415eafc6f5091935fed131",
    "private-subset-view.js": "2a801d1c3e9495cb855893e03f01d0d93da0e87a956aa9c84bba3b8e75671356",
    "watchlist.js": "6d707c1f7beb0d4ceaf32cea18320049bbd1ba768bf91578ba6a664596f536cf",
    "sec-m3-adapter.js": "04c835ddbf7f7c5b9e5ebd77571d8fdac70444f673b00092579f3bef4e341de6",
    "private-subset.js": "8016f30888b77c3b92ce1b5e0c11e542505a04ad6865c169c9525c78ebf4bd71",
    "engine-preview.js": "4aac27a64e569b7d6b15335384581e7f33fb51163a1bffc4a541270fc075dfa0",
    "profile-defaults.js": "4481bff54856e506f52342beb9e3747eb1dd167639b40a0d7af99290d32af3cc",
    "device-profiles.js": "c0b74654a33347ec9f7f797d79d1b8b523194961ae15b4f476036870b931e882",
    "public-screens.js": "ad86eace5369424b639478d37140072a805a27df6e7d4277213318d2c7ac6355",
    "pwa.js": "84f1225bacd8c41fd0a82b65c19d28cc02e0e739ae384614df35a9801da418b0",
    "service-worker.js": "130c082cfd1fd50d68441a05daa9cf41450ea6822f2576dd949adb19561d81d8",
    "icon-512.png": "7a19587556ba133a21622288ec66a48095b933461f10475e96cf7b3a43afee88",
    "icon-192.png": "31510ec0c9a07bb7e9de51f8769189d21f69b66c4cdb8a39d996373dce828e3b",
    "manifest.json": "b4a949507c0859ee3ec158f0a6eaa6ec9cefc5c0e7e630715336817b9c248f8c",
    "offline.html": "84dabe85364d57ca5ab49018e195871504df443a714e819fdb6a3c614be79bb5",
    "sec-reported.js": "ec1bf6645f8a02412df68a7a5147b3d68f8467e8a742bc781ec25678f21ad7f2",
    "google-sheet-setup.js": "24d8c0bb60310c104b7d5ec08292330d62d1a32f33a61eae4e76b5489747f471",
    "private-trades.js": "86d59b4c5ef341ab47f1892fe65b483ca8256e367cfde06e1c9a0b580530fb9f",
    "technical-chart.js": "64b581fd186cdcb39f31def58412052dfa777dc2920a4f2432c1842b19c65eb8",
    "chart-indicators.js": "30cf6571f32c0496acd247099feb5f71fce0acf8870dcd78781018b872291fcc",
    "device-backup.js": "ab938511333c87255a4f9ae6102cc9508cca4c78128f7183771d87391c6e511f",
    "sec-m2-candidates.json": "3499f945e45bdc61b627148755cb017008568e49d6cc1276c9a2b780c412b816",
    "actual-catalog.json": "f73548d955a722e91e732074cfc3686e2c1e5dc70784b4134e9294ba46e7256e",
    "app-config.js": "5dc9cbd509264e88b827c96ddf0bd888637c9bcdfd16235c3e38c2086e91b82b",
    "app.js": "8204e40b848a68396bda23fb9f1197828907c886884e7a99d1c8aa7ea969ca19",
    "data.json": "7afba9f30d4322ae67593cba3866db78d0d0f7822c32e2eff375497156b5b7e1",
    "device-actual.css": "319b0aa07e9f47f19cadaae773fa555a65d9c52f3c28320604e382872fa8d4b9",
    "device-actual.js": "1cfae1a928e74055b1536e1b8dbe26509780eb3eed2f79b3a1963de4feb25f60",
    "device-market.js": "c0824cb68bc2121ea88b2cd10081336f394736b773189c3f2ba865fa799261a7",
    "entities.json": "8a452006b4821bb0c1fed05de17a2a81da7457fe546f6d9161a1d8b4bda16ac2",
    "entity-search.js": "97d54a29f9336cfbc67a10c886ab8de5676a542a0b59cb122d77ba2ab861319a",
    "google-sheet-core.js": "9825b81e6f81c87c2608979b533f2ad5e7bfba63c4e88d6ce292940958be624c",
    "google-sheet-quotes.js": "59c8bab257051b7b5b4982ba4bedfa998a2e14c63852caef643aee6072f249b2",
    "google-sheet-quotes.css": "5e37d704c69891893a8ca81a9a41d7f268696be210774609cc9c1d7ac7db5237",
    "index.html": "3a5bc819619eb0d8d9446fde6a135c7d5ed3d5fa9ef2ebcdc3206dbb22f4744e",
    "locale.js": "f3537029f859a0958c9d2440b7fcc021fef96b2845ff3320ad8b8ae045f09dc2",
    "private-history.css": "d4ce930e901e2b67b2eb6d57c8795f77be3b9f1650efa85dad6e524419c42028",
    "private-history.js": "c8477c65c211094db0ebad90a40514e5bee9e7b7b8cbe82e05ae850aee7de182",
    "research.html": "03fcceb4f7c080e76d7fd1cf27477502284fa1fa24ca16f99c79f43c24751309",
    "style.css": "8c88942eeb1fff9eb9ca73dc5fd1fba744b75a55ad54f449063ac3b007164c9c",
    "sec-disclosures.js": "849cbfbf2b21badd52c06cf5887dcd259e08864552a76fde39f065f82c6a7194",
    "sec-qgv2.js": "419b49c42921b2792a18ff051e3864620cfacec3918b3b98e74adf90d61cb48d",
    "price-store.js": "52b723d9e7dfc189252a870c57f5a044373427d3a9009bb9a119c322ebb8c4de",
    "qgv2-inputs.js": "f53cc206b1655f7a8602f8f0aab12d8199cd58a4818561eff02a9c18294c251f",
    "scoring-default.js": "02eae2182de717bf0620e9616fe2aabd78c7ec8484c60d65f4231262df868beb",
    "qgv-v2.js": "0f06a8904b156e18f503c47844b540b4b12f3368933ff21bc3157afe482b3717",
    "qgv-scores.js": "dd16b0deca5e5d669f0a3ec1755859af840ff535c8e1e1a040414bc3505ded87",
    "playbook-screen.js": "1132a15c8d5fe91dd04aa9df1731879407a86c7d7e65a9fa55d833fb2e9efc3d",
    "news-signals.js": "c0e4d3a23afbd5162508f54aab98a836ecfae9980796f66d13a6019c0fba4405",
    "dart-disclosures.js": "7ea88fa32ffa0be446e28f3b91532532bf2b98073f31d4ec1d62db8e73d7efdf",
    "macro-lights.js": "d64e3d4c68fb8c0ffdbfe16ad3220af2648bda4d331edd387ca337d52c42d741",
    "sec-disclosures.js": "849cbfbf2b21badd52c06cf5887dcd259e08864552a76fde39f065f82c6a7194",
    "theme-boot.js": "4aaf08ecd900e1216a95159a277f8a7c51c32e41784f1ac9530ecf1dc77a6f2c",
    "theme.css": "a5e89c0da9b0af8ee3662989c33e2c4c19f2a4bf14ef0e864a41ff2f4e4fa3f7",
    "app-shell.js": "e7cdd03821e5f543925c16bbb2fb67b977df4c1d5c88e2f532f86cb3b8d31199",
    "home-screen.js": "5cf68ce2b98a7bfb90251fabbf7f357a5638408467ee4d1479c05d45da98da73",
    "home-quotes.js": "46487b40e170c3291b023bebcb0fd01da19bb3beb53bfad3006be6377cfe3a96",
    "doodles.js": "413afcb07c5ef5f4edcb0ab544ba61a7d19954db0951ccdf85742c04cf5bb57e",
    "ia-screens.js": "314618697c70a441b4367e4192af61995c41910158d4d404ed595d63d5bc6219",
    "universe-company.js": "22b3af7a66d980f65eed67b240618e2da474b88cea99846cc2d604e410634a73",
    "universe-company.css": "5b1b0236290f91c95b7f25d49bc93d032bf1718754c1cfae7789e92bb74b11b8",
    "stat-radar.js": "c1582fbe290881c6389c50c6f5a1a0cb5ca358509510c12a7b0c81f8006f7179",
    "stat-radar.css": "bae106529a7b0897d9fe41fa8cb60630e15ae961bdf25ef9ea38b21d247d1b6d",
    "v-coverage.js": "bc380a3950993e22b4ae8e965764e4a21806004f96276123da3896ff15280680",
    "price-time.js": "9b786d04615f3a8907f8f936db78ab3fd477808eadc27814e615ffbb7dddbc0f",
    "data-refresh.js": "42dbf569450963a19887e6fec85c28311ad0bf022ea584329ef9bcc1475f28c8",
    "v-coverage.css": "185302f9f5aa9542d2caadfa03363f084bf837e8e1ea2998da49fa1db8af9364",
}
ALLOWED_NAMES = frozenset(APPROVED_SHA256) | {SEC_PUBLIC_FILENAME, UNIVERSE_SHARES_FILENAME, UNIVERSE_QG_FILENAME, CLASSIFICATION_FILENAME, FORWARD_LEDGER_FILENAME, UNIVERSE_CODES_FILENAME, COMPANY_NAMES_FILENAME, UNIVERSE_DOMAINS_FILENAME, COMPANY_LOGOS_FILENAME, QGV2_FILENAME, DISCLOSURES_FILENAME, NEWS_SIGNALS_FILENAME} | set(SCREEN_FILENAMES) | set(DART_FILENAMES)
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 128
MAX_JSON_DEPTH = 64

SENSITIVE_KEYS = frozenset({
    "rank", "marketcaprank", "rankislowerbound", "vscore", "totalscore",
    "periodreturn", "realizedreturn", "dailyreturn", "performance",
    "quantity", "quantities", "averagecost", "avgcost", "amount", "cash",
    "balance", "account", "accountnumber", "accountid", "marketvalue",
    "money", "moneyvalue", "mcap", "cutoffmcap", "marketcap",
    "marketcapitalization", "costbasis", "purchaseprice", "networth",
    "holdings", "positions", "actualholdings", "investedamount",
    "totalcost", "cost", "price", "valueamount", "cashbalance",
    "spreadsheetid", "spreadsheeturl", "accesstoken", "refreshtoken", "clientsecret",
})
SECRET_PATTERNS = (
    re.compile(r"(?i)(?<![a-z0-9._%+\-])[a-z0-9._%+\-]+@[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}"),
    re.compile(r"(?<![A-Za-z0-9_])ya29\.[A-Za-z0-9._~-]+"),
    re.compile(r"https://docs\.google\.com/spreadsheets/(?:u/\d+/)?d/[A-Za-z0-9_-]{20,100}"),
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)(?<!\w)(?:api[_-]?key|access[_-]?token|refresh[_-]?token|"
        r"auth[_-]?token|client[_-]?secret|private[_-]?key|password|secret|token)"
        r"\s*[\"']?\s*[:=]\s*[\"'][^\"'\r\n]+[\"']"
    ),
    re.compile(r"(?i)authorization\s*:\s*[\"']?bearer\s+[a-z0-9._~+/=-]{8,}"),
)


def _receipt(violations: Counter, files_scanned: int) -> dict:
    return {
        "pages_artifact_guard": "FAIL" if violations else "PASS",
        "files_scanned": files_scanned,
        "violations": dict(sorted(violations.items())),
    }


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ValueError("nonfinite JSON number")


def _populated(value: object) -> bool:
    # Zero and false are populated. Container contents need not be numeric.
    return value is not None and value != "" and value != [] and value != {}


def _inspect_json(value: object, violations: Counter, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise ValueError("JSON nesting limit")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite JSON number")
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", key.casefold())
            if normalized in SENSITIVE_KEYS and _populated(child):
                violations["sensitive_json_fields"] += 1
            if key in {"schema", "schema_version"} and isinstance(child, str):
                if re.search(r"device[-_]actual[-_](?:holdings|export)(?:/|$)", child, re.I):
                    violations["private_device_schema"] += 1
            _inspect_json(child, violations, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _inspect_json(child, violations, depth + 1)
    elif isinstance(value, str):
        # JSON escapes must not hide a contact address from the raw-text scan.
        if SECRET_PATTERNS[0].search(value):
            violations["secret_patterns"] += 1


def _check_payload(name: str, payload: bytes, violations: Counter) -> None:
    try:
        if name in {'icon-192.png', 'icon-512.png'}:
            if not payload.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(payload).hexdigest() != APPROVED_SHA256[name]:
                violations['unapproved_content'] += 1
            return
        text = payload.decode("utf-8", errors="strict")
        if any(ord(character) < 32 and character not in "\t\n\r" for character in text):
            raise ValueError("binary control character")
        violations["secret_patterns"] += sum(len(pattern.findall(text)) for pattern in SECRET_PATTERNS)
        if not violations["secret_patterns"]:
            del violations["secret_patterns"]
        if name.endswith(".json"):
            value = json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
            _inspect_json(value, violations)
            if name == "sec-m2-candidates.json":
                try:
                    require_public_candidates(value)
                except ValueError:
                    violations["m2_candidate_boundary"] += 1
            if name in {'data.json', 'entities.json', 'actual-catalog.json'}:
                try:
                    if name == 'data.json':
                        require_public_bundle(value)
                    else:
                        require_public_catalog(name, value)
                except PublicPriceBoundaryError:
                    violations['public_price_boundary'] += 1
            payload = json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode("utf-8", errors="strict")
        if name == SEC_PUBLIC_FILENAME:
            try:
                require_public_inputs(value)
            except ValueError:
                violations["sec_public_boundary"] += 1
        elif name == CLASSIFICATION_FILENAME:
            try: require_public_classification(value)
            except ValueError: violations['classification_boundary'] += 1
        elif name in SCREEN_FILENAMES:
            try: require_public_screen(name, value)
            except ValueError: violations['public_screen_boundary'] += 1
        elif name == UNIVERSE_SHARES_FILENAME:
            try: require_universe_shares(value)
            except ValueError: violations['universe_shares_boundary'] += 1
        elif name == UNIVERSE_CODES_FILENAME:
            try: require_universe_codes(value)
            except ValueError: violations['universe_codes_boundary'] += 1
        elif name == COMPANY_NAMES_FILENAME:
            try: require_company_names_ko(value)
            except ValueError: violations['company_names_boundary'] += 1
        elif name == QGV2_FILENAME:
            try: require_qgv2(value)
            except ValueError: violations['qgv2_boundary'] += 1
        elif name == COMPANY_LOGOS_FILENAME:
            try: require_company_logos(value)
            except ValueError: violations['company_logos_boundary'] += 1
        elif name == UNIVERSE_DOMAINS_FILENAME:
            try: require_universe_domains(value)
            except ValueError: violations['universe_domains_boundary'] += 1
        elif name == UNIVERSE_QG_FILENAME:
            try: require_universe_qg(value)
            except ValueError: violations['universe_qg_boundary'] += 1
        elif name == DISCLOSURES_FILENAME:
            try: require_sec_disclosures(value)
            except ValueError: violations['sec_disclosures_boundary'] += 1
        elif name == NEWS_SIGNALS_FILENAME:
            try: require_news_signals(value)
            except ValueError: violations['news_signals_boundary'] += 1
        elif name in DART_FILENAMES:
            try: require_dart_public(name, value)
            except ValueError: violations['dart_public_boundary'] += 1
        elif name == FORWARD_LEDGER_FILENAME:
            try: require_forward_ledger(value)
            except ValueError: violations['forward_ledger_boundary'] += 1
        elif hashlib.sha256(payload).hexdigest() != APPROVED_SHA256[name]:
            violations["unapproved_content"] += 1
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        violations["invalid_format"] += 1


def _read_regular(fd: int, limit: int, violations: Counter) -> bytes | None:
    metadata = os.fstat(fd)
    if not stat.S_ISREG(metadata.st_mode):
        violations["nonregular_entries"] += 1
        return None
    if metadata.st_size > limit:
        violations["oversized_files"] += 1
        return None
    with os.fdopen(fd, "rb", closefd=False) as handle:
        payload = handle.read(limit + 1)
    if len(payload) > limit:
        violations["oversized_files"] += 1
        return None
    return payload


def scan_artifact(artifact_dir: str | Path) -> dict:
    """Return only category counts; never return artifact paths or contents."""
    violations = Counter()
    files_scanned = 0
    seen = set()
    try:
        # Directory fd and no-follow child opens also prevent check/open races.
        root_fd = os.open(artifact_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with os.scandir(root_fd) as entries:
                for index, entry in enumerate(entries):
                    if index >= MAX_ENTRIES:
                        violations["excessive_entries"] += 1
                        break
                    name = entry.name
                    if name not in ALLOWED_NAMES:
                        violations["unexpected_entries"] += 1
                    else:
                        seen.add(name)
                    if not entry.is_file(follow_symlinks=False):
                        violations["nonregular_entries"] += 1
                        continue
                    if name not in ALLOWED_NAMES:
                        continue
                    try:
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
                        try:
                            payload = _read_regular(fd, MAX_FILE_BYTES, violations)
                        finally:
                            os.close(fd)
                        if payload is not None:
                            files_scanned += 1
                            _check_payload(name, payload, violations)
                    except OSError:
                        violations["unreadable_entries"] += 1
        finally:
            os.close(root_fd)
        missing = len(APPROVED_SHA256.keys() - seen)
        if missing:
            violations["missing_files"] += missing
    except (OSError, ValueError):
        violations["invalid_artifact_directory"] += 1
    return _receipt(violations, files_scanned)


def _plain_tar_layout(payload: bytes, violations: Counter) -> bool:
    """Inspect physical headers too: tarfile otherwise hides extension records.

    The upload step must set TAR_OPTIONS='--owner=0 --group=0 --numeric-owner'.
    Only ordinary GNU/USTAR headers, zero padding and the zero EOF trailer are
    accepted. Owner names may also be 'root' for equivalent local GNU fixtures.
    """
    block_size = tarfile.BLOCKSIZE
    if len(payload) % block_size or len(payload) < block_size * 2:
        violations["invalid_archive"] += 1
        return False
    offset = 0
    for _ in range(MAX_ENTRIES + 1):
        block = payload[offset:offset + block_size]
        if block == bytes(block_size):
            if len(payload) - offset < block_size * 2 or any(payload[offset:]):
                violations["invalid_archive"] += 1
                return False
            return True
        if len(block) != block_size:
            violations["invalid_archive"] += 1
            return False
        member = tarfile.TarInfo.frombuf(block, encoding="utf-8", errors="strict")
        if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE}:
            violations["nonregular_entries"] += 1
            if member.type in {tarfile.XHDTYPE, tarfile.XGLTYPE,
                               tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK}:
                violations["unsupported_archive_metadata"] += 1
            return False
        if member.type == tarfile.DIRTYPE and member.name not in {".", "./"}:
            violations["nonregular_entries"] += 1
            return False
        name_field = block[:100]
        name_bytes = name_field.split(b"\0", 1)[0]
        owner_fields = ((265, member.uname), (297, member.gname))
        metadata_valid = (
            block[257:265] in {b"ustar  \0", b"ustar\00000"}
            and member.uid == 0 and member.gid == 0
            and member.devmajor == 0 and member.devminor == 0
            and member.mode in {
                0o600, 0o644, 0o700, 0o755,
                stat.S_IFREG | 0o600, stat.S_IFREG | 0o644,
                stat.S_IFDIR | 0o700, stat.S_IFDIR | 0o755,
            }
            and not member.linkname and block[157:257] == bytes(100)
            and name_field == name_bytes.ljust(100, b"\0")
            and not any(block[345:])
        )
        for start, owner in owner_fields:
            metadata_valid = metadata_valid and owner in {"", "root"}
            metadata_valid = metadata_valid and block[start:start + 32] == owner.encode().ljust(32, b"\0")
        for start, length in ((100, 8), (108, 8), (116, 8), (124, 12),
                              (136, 12), (148, 8), (329, 8), (337, 8)):
            field = block[start:start + length]
            number, separator, padding = field.partition(b"\0")
            # No ignored bytes after a terminator; GNU checksum ends NUL-space.
            metadata_valid = metadata_valid and bool(re.fullmatch(rb" *[0-7]* *", number))
            metadata_valid = metadata_valid and (not separator or all(byte in b" \0" for byte in padding))
        if not metadata_valid:
            violations["unsupported_archive_metadata"] += 1
            return False
        if member.size < 0 or member.size > MAX_FILE_BYTES:
            violations["oversized_files"] += 1
            return False
        if member.type == tarfile.DIRTYPE and member.size:
            violations["invalid_archive"] += 1
            return False
        data_end = offset + block_size + member.size
        next_offset = ((data_end + block_size - 1) // block_size) * block_size
        if next_offset > len(payload) or any(payload[data_end:next_offset]):
            violations["invalid_archive"] += 1
            return False
        offset = next_offset
    violations["excessive_entries"] += 1
    return False


def validate_pages_tar(archive_path: str | Path) -> dict:
    """Check a raw GitHub Pages artifact.tar in place, without extracting it."""
    violations = Counter()
    files_scanned = 0
    seen = set()
    root_seen = False
    try:
        fd = os.open(archive_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode):
                violations["nonregular_entries"] += 1
                return _receipt(violations, files_scanned)
            if metadata.st_size > MAX_ARCHIVE_BYTES:
                violations["oversized_archive"] += 1
                return _receipt(violations, files_scanned)
            with os.fdopen(fd, "rb", closefd=False) as handle:
                payload = handle.read(MAX_ARCHIVE_BYTES + 1)
                if len(payload) > MAX_ARCHIVE_BYTES:
                    violations["oversized_archive"] += 1
                    return _receipt(violations, files_scanned)
                if not _plain_tar_layout(payload, violations):
                    return _receipt(violations, files_scanned)
                # Pages upload uses an uncompressed tar. Compression and PAX
                # metadata are outside the approved transport shape.
                with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as archive:
                    for index, member in enumerate(archive):
                        if index >= MAX_ENTRIES:
                            violations["excessive_entries"] += 1
                            break
                        if archive.pax_headers or member.pax_headers:
                            violations["unsupported_archive_metadata"] += 1
                        if member.name in {".", "./"} and member.type == tarfile.DIRTYPE:
                            if root_seen:
                                violations["duplicate_entries"] += 1
                            root_seen = True
                            continue
                        name = member.name[2:] if member.name.startswith("./") else member.name
                        if name not in ALLOWED_NAMES:
                            violations["unexpected_entries"] += 1
                        elif name in seen:
                            violations["duplicate_entries"] += 1
                        else:
                            seen.add(name)
                        if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE}:
                            violations["nonregular_entries"] += 1
                            continue
                        if name not in ALLOWED_NAMES:
                            continue
                        if member.size < 0 or member.size > MAX_FILE_BYTES:
                            violations["oversized_files"] += 1
                            continue
                        source = archive.extractfile(member)
                        if source is None:
                            violations["invalid_archive"] += 1
                            continue
                        with source:
                            payload = source.read(MAX_FILE_BYTES + 1)
                        if len(payload) != member.size:
                            violations["invalid_archive"] += 1
                            continue
                        files_scanned += 1
                        _check_payload(name, payload, violations)
        finally:
            os.close(fd)
        missing = len(APPROVED_SHA256.keys() - seen)
        if missing:
            violations["missing_files"] += missing
    except (OSError, ValueError, tarfile.TarError, UnicodeError, RecursionError, OverflowError):
        violations["invalid_archive"] += 1
    return _receipt(violations, files_scanned)


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        print(json.dumps(_receipt(Counter({"invalid_arguments": 1}), 0), sort_keys=True))
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    parser = _SafeArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--artifact-dir")
    inputs.add_argument("--pages-artifact")
    args = parser.parse_args(argv)
    receipt = scan_artifact(args.artifact_dir) if args.artifact_dir else validate_pages_tar(args.pages_artifact)
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["pages_artifact_guard"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
