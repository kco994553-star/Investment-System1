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
import struct
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
from investment_system.macro.evidence_lines import FILENAME as MACRO_EVIDENCE_FILENAME, require_macro_evidence

# Reviewed public output, not hashes derived from potentially changed inputs.
APPROVED_SHA256 = {
    "target-v1-builder.js": "6b0dc3d3255719c7d287f28b8cca16b43ed2739e78531d6ff9b43a406a847662",
    "target-v1-config-defaults.js": "a8b126e7b8200f236d4e0c52a728ce14476aa6cad6f45e1b23f97dbb0ebc8787",
    "target-v1-screen.js": "5bf8cde5adaccfa102a74752babdaf380d0151afa1ad3402ec59afb47619e0a0",
    "playbook-engine.js": "b708a1772b4cd8e1af731cffdacbfab478d03c9c4e1e5fd663537babd64ee7d8",
    "playbook-config-defaults.js": "b0dd6aeed54a11082953b83aa30497c99dd454040e7e7adbc46cdd4c0a1221a6",
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
    "table-sort.js": "cd483582e80b7df2b5a5ffb16af84e7200ebfa841ed40fa5cee89bd3d8c338db",
    "pc-layout.css": "d3a270238df767d49ef23ea3d53d60fca62d65dc017af19338269602190af2b4",
    "share-class-groups.js": "088bbfaec559937753533572330a6be3c2f9280910f9f6cf62b53f39119c0997",
    "forward-validation.js": "85432c469bce8466d2df24b90e2caf1985c2036d596e37725e9073368216f009",
    "daily-report.js": "c719625827b965f0ac26b766a69ab46ed9d3c923660a44675074791b9f085389",
    "sec-universe-shares.js": "7a64bf6c280b81258ebd13e78b6761876f7056565f18ba9e64da897d953f600d",
    "virtual-trading-v-history.js": "944124763c2682dff373f9ec86e8b938ee2400f3084b5e3d62d8b44c8bd8099f",
    "virtual-trading-signals.js": "b8d73d216d9697bea31f15f0061831f81a144b518b5aa5cc54ba4620dafbe6ef",
    "sec-universe-qg.js": "92664e67228854456739880f2314b77da73155227995065e63d9711207fa3a2c",
    "sec-qgv2.js": "419b49c42921b2792a18ff051e3864620cfacec3918b3b98e74adf90d61cb48d",
    "device-valuation.js": "06669cda863cd4dfa87108f54e03b75c9321989967da7ed54b03c921143cfedf",
    "dcf-parameters-defaults.js": "3f9498ef6177b9dcd3c4fa80077c8480750be93668f57bd5ed5ed3b5509a8473",
    "classification-screens.js": "23ed7302742bf769068ef128dc48075fe6c88d6610585356e6b4e88d14db0a8f",
    "manager-styles-v0.js": "b32f434b17ba00d6ec1e4813517884e5caded996779df9b1976dfc38964ab38e",
    "screen-detail.js": "d4bed4772a5d70daf6d03491fbc0acfbd0b878789b55de2fdfdf13706f2f354b",
    "virtual-trading.js": "41a834f13d86ed2bd6a046cf63788992350294714ee9b9ee159ae50de8e20206",
    "technical-cards.js": "cc6164ac1ca510bb7fddd3403e128198db90c7d7a98b860792bb53df5c1bf814",
    "leaderboard-screen.js": "083a06188d354ff6060bc80134dab544dd8d369150b136e072f7b8b0b119d43c",
    "portfolio-screen.js": "97b7c8f0014a90e9308d1a49f992b05f2f31aac244ef75b65c388c9bc471c9c2",
    "company-screen.js": "5c55833a4a0cf36f827f41b98d9e5c783524489a4aae2dbdca860c0a4628bfae",
    "ops-status.js": "bccccba913e0887ee2bb3c38fd61f27fcc2a6d37acb67aeeffea227df422c7a9",
    "type-config-defaults.js": "8b287dde54fb194469bd13d62c356e51eb78c4c04c415eafc6f5091935fed131",
    "private-subset-view.js": "bd93b7d5cd7d5c13950d5786a77fabb6a9c1d2d41cfdd328773c1e941d982237",
    "watchlist.js": "6d707c1f7beb0d4ceaf32cea18320049bbd1ba768bf91578ba6a664596f536cf",
    "sec-m3-adapter.js": "04c835ddbf7f7c5b9e5ebd77571d8fdac70444f673b00092579f3bef4e341de6",
    "private-subset.js": "8016f30888b77c3b92ce1b5e0c11e542505a04ad6865c169c9525c78ebf4bd71",
    "engine-preview.js": "4aac27a64e569b7d6b15335384581e7f33fb51163a1bffc4a541270fc075dfa0",
    "profile-defaults.js": "4481bff54856e506f52342beb9e3747eb1dd167639b40a0d7af99290d32af3cc",
    "device-profiles.js": "4a30e7ca4890a010e662836fbb612942c7b0c0d2434769dde39b37895445f487",
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
    "chart-bars.js": "eca373c58fe78c9a0135962ef6fe3421c441345e91bb7cebe6c4de9927efa01b",
    "pattern-config-defaults.js": "fe02afed1c54b1be999620d34666cddadb42fee751be581db1134466ffb8a324",
    "pattern-engine.js": "1e23afd43c9b4c8aa658371dd742f9cc6059bfbe73ee697870c36d0d011c9a5d",
    "pattern-history.js": "ae60f0458a11550152d76c50981ae786bffc1d678589feb2062c638d0a925f45",
    "device-backup.js": "27e58a096ea0d846d29fc7a796c4b6f684727b2c51025a83eee7936948862e8e",
    "sec-m2-candidates.json": "3499f945e45bdc61b627148755cb017008568e49d6cc1276c9a2b780c412b816",
    "actual-catalog.json": "f73548d955a722e91e732074cfc3686e2c1e5dc70784b4134e9294ba46e7256e",
    "app-config.js": "5dc9cbd509264e88b827c96ddf0bd888637c9bcdfd16235c3e38c2086e91b82b",
    "app.js": "1fd9cb3bfef16d4e827fa89581c667248e10aab72d2075d79371c23d37701152",
    "data.json": "7afba9f30d4322ae67593cba3866db78d0d0f7822c32e2eff375497156b5b7e1",
    "device-actual.css": "57a6f74deb228391ae65085bde62f3cef2126937cf5063dda41f4807abf44845",
    "device-actual.js": "aa9acb0cd0f8a48ed6a7370a9e2e9372d5c90db609f57a973ebbf4197a617dc1",
    "device-market.js": "c0824cb68bc2121ea88b2cd10081336f394736b773189c3f2ba865fa799261a7",
    "entities.json": "8a452006b4821bb0c1fed05de17a2a81da7457fe546f6d9161a1d8b4bda16ac2",
    "entity-search.js": "97d54a29f9336cfbc67a10c886ab8de5676a542a0b59cb122d77ba2ab861319a",
    "google-sheet-core.js": "9825b81e6f81c87c2608979b533f2ad5e7bfba63c4e88d6ce292940958be624c",
    "google-sheet-quotes.js": "59c8bab257051b7b5b4982ba4bedfa998a2e14c63852caef643aee6072f249b2",
    "google-sheet-quotes.css": "5e37d704c69891893a8ca81a9a41d7f268696be210774609cc9c1d7ac7db5237",
    "index.html": "23a53e1b8bc828899a681dfe13420dbdaeba5d4e7bb117858ec262640d2066fb",
    "locale.js": "f3537029f859a0958c9d2440b7fcc021fef96b2845ff3320ad8b8ae045f09dc2",
    "private-history.css": "d4ce930e901e2b67b2eb6d57c8795f77be3b9f1650efa85dad6e524419c42028",
    "private-history.js": "289a8a2c1053a0d280504cd785d188316b5ac9fd99eaa5590a3aa57c82e3958c",
    "research.html": "eb5f673078ded25737b85b532c6d8c88f457d14bf1c433299e7e70be022aa57c",
    "style.css": "a3deb2677f4335021a37ba0546823732aade654e3b7374ad4e39d2ff8e5e1841",
    "sec-disclosures.js": "849cbfbf2b21badd52c06cf5887dcd259e08864552a76fde39f065f82c6a7194",
    "sec-qgv2.js": "419b49c42921b2792a18ff051e3864620cfacec3918b3b98e74adf90d61cb48d",
    "price-store.js": "ce3a9ffc1cfbe36d1d1d6fa5761427bffeaf860628c1d36c05906ee2db6a1f89",
    "qgv2-inputs.js": "f53cc206b1655f7a8602f8f0aab12d8199cd58a4818561eff02a9c18294c251f",
    "scoring-default.js": "02eae2182de717bf0620e9616fe2aabd78c7ec8484c60d65f4231262df868beb",
    "qgv-v2.js": "0f06a8904b156e18f503c47844b540b4b12f3368933ff21bc3157afe482b3717",
    "qgv-scores.js": "02573dc9b02839af4220d4a63e0685a41c7b99f66fc9ebe846e4f42ed2f37866",
    "playbook-screen.js": "5d432af74fdda5dae3e467158885c366fe0bde6277264a77be4c585f75129207",
    "news-signals.js": "6a85c92329ca6968175d357ec10a81198b692d762a29ab1a30374a3f0b3c718c",
    "dart-disclosures.js": "7ea88fa32ffa0be446e28f3b91532532bf2b98073f31d4ec1d62db8e73d7efdf",
    "macro-lights.js": "5a406856c8ab4b88d519e57aebee6909f6dac671d3064cca1923e0717d9f648e",
    "macro-cycle-ring.js": "cacb0a4a21774e9c18d29c9831d13862b9866a187ebadbe0d71084472232b012",
    "macro-cycle-ring.css": "14567f0ec84436066b814a448efe3c16bc98c8066cf23cd21d40835d049510ca",
    "sec-disclosures.js": "849cbfbf2b21badd52c06cf5887dcd259e08864552a76fde39f065f82c6a7194",
    "theme-boot.js": "4aaf08ecd900e1216a95159a277f8a7c51c32e41784f1ac9530ecf1dc77a6f2c",
    "theme.css": "4cd7dc3f0c69a9f99cf946aa61f76f3cefa12e4d529b3d22b8fb7721f63b932c",
    "app-shell.js": "a1a789dfb521102503f3715c221015ca56d5f2220c7e2ddb5a9f26c628004d14",
    "home-screen.js": "9979acbdf24277c3d612b4b1929d693ca9cdecd1f98a190feaa84989e5e36d4a",
    "home-quotes.js": "46487b40e170c3291b023bebcb0fd01da19bb3beb53bfad3006be6377cfe3a96",
    "doodles.js": "413afcb07c5ef5f4edcb0ab544ba61a7d19954db0951ccdf85742c04cf5bb57e",
    "ia-screens.js": "e1b95555be736df9371b0b89d31caa8608740f0d3f8f2a4c26c946a67ea22ea0",
    "universe-company.js": "f28e53e7269932790d45339a80761db451664f0a7b44b7d173b759050a946d82",
    "universe-company.css": "5b1b0236290f91c95b7f25d49bc93d032bf1718754c1cfae7789e92bb74b11b8",
    "stat-radar.js": "f46686ac9391e398d9c0cc0af19c00aa9de2b32cd1a37cc5c4abb0dabb047750",
    "stat-radar.css": "1afcc9df3d0eeadb87b7d80251ef17091146bf62f2da40a9f7e249b2969bd6db",
    "v-coverage.js": "8031a5cf658ecc287df71dcbe5f6fdc61cc754057e39086eefa210847d37aa4c",
    "price-time.js": "9b786d04615f3a8907f8f936db78ab3fd477808eadc27814e615ffbb7dddbc0f",
    "data-refresh.js": "ee4d9745536dd0c698518820d1c82be297d3b28f2e0075601c21c5d000a0a76d",
    "v-coverage.css": "185302f9f5aa9542d2caadfa03363f084bf837e8e1ea2998da49fa1db8af9364",
    "macro-evidence.js": "b87449fcb0edea5de6a6ac74cd9e7579ad81a28af970f2fc2f59f7594207070b",
    "macro-evidence.css": "5270ef2e2c80eb70125ed39f8fbef5f3f0d87172d3dff3a79c888b92ec9520cd",
    # Self-hosted chart renderer (P1-7): lightweight-charts 5.2.1 npm file unmodified, upstream LICENSE/NOTICE, third-party notices.
    "chart-renderer.js": "c6053c2633788813d363d3346833f416fa954fbf8db7e1e18252b191c0dd040b",
    "chart-workbench.js": "05d5cc2a89e68fe9e22286c6c8cea47048592e13e4ad8bec5f1299a122ee346c",
    "chart-workbench.css": "6824369fd724e8ebd36d62ea498318dceab65cd12c69975f7b3f542048ebfb9f",
    "lightweight-charts-5.2.1.standalone.js": "e21cc5caa0226ef30bd8549c50b9ef926615f2a4ee6b4e486353477a55f598cf",
    "lightweight-charts-5.2.1.LICENSE.txt": "70c9d5382506dd184465425c08a99ad9bd6d9ac1313c252968ba0b585e5ef823",
    "lightweight-charts-5.2.1.NOTICE.txt": "f76c6afab94884448f0426e30d6e9d555ca7247894cd3484e477d2f87513036e",
    "third-party-notices.txt": "6f24b5e4df26683877769364a388c8eac361de2c6a1caab169270d3b8b400cff",
    # Self-hosted SIL OFL 1.1 fonts (IA-11, owner "호스팅해" 2026-10-20): google/fonts 47d54ca1 Jua/Gaegu Regular, subset to
    # Latin + KS X 1001 Hangul as WOFF2 (binary, see FONT_FILES), and the unmodified upstream OFL texts.
    "jua-regular-ksx1001.woff2": "2699d0318876afef41d823cec84d30d08d98ab6723d9958b6d5f79f57ade1cc2",
    "gaegu-regular-ksx1001.woff2": "91e086f4668132cd51a70ba2b6d7d9706da87f8a7f8be4b198f968ddb69894c0",
    "jua-OFL.txt": "44a7c6e4c5572392ae122d3b1d8c6ba6fd640a7797e675384585d947f2773e3c",
    "gaegu-OFL.txt": "53a9ce47085d9fef613c7ecb3730dc80d25962510bbea231b89564f58240f251",
}
# Font exception (IA-11, owner approval 2026-10-20, exact scope): the ONLY binary files besides the two PWA icons are
# these two names, and only at the artifact root. Both scan modes match the full relative path against ALLOWED_NAMES
# (the directory scan reads root entries only; a tar member under a directory keeps its directory in the name), so the
# same file name anywhere else, or any other *.woff2 name, is an unexpected entry. No extension-wide allowance exists.
# For these two files only, the UTF-8 decode and the text secret-pattern scan are skipped (binary payload); instead each
# must pass the tighter FONT_MAX_BYTES cap, a structural WOFF2 header check and its pinned SHA-256. Every other file,
# including the fonts' OFL licence texts, still goes through all text checks.
FONT_FILES = frozenset({"jua-regular-ksx1001.woff2", "gaegu-regular-ksx1001.woff2"})
FONT_MAX_BYTES = 256 * 1024  # pinned subsets are 187,292 and 83,968 bytes; tighter than MAX_FILE_BYTES on purpose
ALLOWED_NAMES = frozenset(APPROVED_SHA256) | {SEC_PUBLIC_FILENAME, UNIVERSE_SHARES_FILENAME, UNIVERSE_QG_FILENAME, CLASSIFICATION_FILENAME, FORWARD_LEDGER_FILENAME, UNIVERSE_CODES_FILENAME, COMPANY_NAMES_FILENAME, UNIVERSE_DOMAINS_FILENAME, COMPANY_LOGOS_FILENAME, QGV2_FILENAME, DISCLOSURES_FILENAME, NEWS_SIGNALS_FILENAME, MACRO_EVIDENCE_FILENAME} | set(SCREEN_FILENAMES) | set(DART_FILENAMES)
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
# 192 (was 128, owner approval 2026-10-20): a real deploy (build + ledger/public data) reached about 131 entries with the
# chart renderer. Only the entry count changes; the allow-list, pinned hashes, size limits and price/personal checks stay.
MAX_ENTRIES = 192
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


def _valid_woff2_header(payload: bytes) -> bool:
    """WOFF2 table directory header (W3C WOFF2 5.1): 48 bytes, big-endian.

    Signature wOF2, a single-font TrueType or CFF flavor (no collection), declared length equal to the real size,
    a sane table count, zero reserved field, a compressed block inside the file, and no extended-metadata or
    private-data block (nothing that could carry extra payload beside the glyph tables).
    """
    if len(payload) < 48:
        return False
    (signature, flavor, length, num_tables, reserved, total_sfnt_size, total_compressed_size, _major, _minor,
     meta_offset, meta_length, meta_orig_length, priv_offset, priv_length) = struct.unpack(">4sIIHHIIHHIIIII", payload[:48])
    return (
        signature == b"wOF2"
        and flavor in (0x00010000, 0x4F54544F)  # TrueType outlines or 'OTTO'
        and length == len(payload)
        and 0 < num_tables <= 64
        and reserved == 0
        and total_sfnt_size > 0
        and 0 < total_compressed_size < length - 48
        and meta_offset == meta_length == meta_orig_length == 0
        and priv_offset == priv_length == 0
    )


def _check_payload(name: str, payload: bytes, violations: Counter) -> None:
    try:
        if name in {'icon-192.png', 'icon-512.png'}:
            if not payload.startswith(b'\x89PNG\r\n\x1a\n') or hashlib.sha256(payload).hexdigest() != APPROVED_SHA256[name]:
                violations['unapproved_content'] += 1
            return
        if name in FONT_FILES:
            # Binary font exception (see FONT_FILES): size cap, WOFF2 structure, pinned hash; no text scans.
            if len(payload) > FONT_MAX_BYTES:
                violations['oversized_files'] += 1
            elif not _valid_woff2_header(payload):
                violations['invalid_font'] += 1
            elif hashlib.sha256(payload).hexdigest() != APPROVED_SHA256[name]:
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
        elif name == MACRO_EVIDENCE_FILENAME:
            try: require_macro_evidence(value)
            except ValueError: violations['macro_evidence_boundary'] += 1
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
