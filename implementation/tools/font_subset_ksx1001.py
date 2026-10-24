"""Reproduce the two self-hosted WOFF2 font subsets (IA-11) from their pinned upstream files.

Provenance (see web_assets/third-party-notices.txt): google/fonts commit
47d54ca1ebb14fd864695f1d39dc734f39017c33, SIL Open Font License 1.1, no Reserved Font Name.

Exact procedure (offline once the sources are on disk; download into a fresh empty directory and run
Python with -I because the sources are downloaded files):

    mkdir <empty-dir> && cd <empty-dir>
    curl -sSfLO https://raw.githubusercontent.com/google/fonts/47d54ca1ebb14fd864695f1d39dc734f39017c33/ofl/jua/Jua-Regular.ttf
    curl -sSfLO https://raw.githubusercontent.com/google/fonts/47d54ca1ebb14fd864695f1d39dc734f39017c33/ofl/gaegu/Gaegu-Regular.ttf
    curl -sSfL -o jua-OFL.txt https://raw.githubusercontent.com/google/fonts/47d54ca1ebb14fd864695f1d39dc734f39017c33/ofl/jua/OFL.txt
    curl -sSfL -o gaegu-OFL.txt https://raw.githubusercontent.com/google/fonts/47d54ca1ebb14fd864695f1d39dc734f39017c33/ofl/gaegu/OFL.txt
    python -m pip install fonttools==4.67.0 brotli==1.2.0
    python -I implementation/tools/font_subset_ksx1001.py --src <empty-dir> --out <output-dir>

The script refuses sources whose SHA-256 differs from the pins below and reports whether each output
matches the SHA-256 pinned in pages_artifact_guard.py. Versions are recorded because a different
fontTools or brotli may produce different (still valid) bytes; the guard pins the reviewed bytes.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

FONTTOOLS_VERSION = "4.67.0"
BROTLI_VERSION = "1.2.0"
UPSTREAM_COMMIT = "47d54ca1ebb14fd864695f1d39dc734f39017c33"
# output name -> (upstream path, upstream source sha256, reviewed output sha256)
FONTS = {
    "jua-regular-ksx1001.woff2": (
        "ofl/jua/Jua-Regular.ttf",
        "769677aef240bfc3b9965f2b50748075bff885e6c6992fc591a3fb268279f898",
        "2699d0318876afef41d823cec84d30d08d98ab6723d9958b6d5f79f57ade1cc2",
    ),
    "gaegu-regular-ksx1001.woff2": (
        "ofl/gaegu/Gaegu-Regular.ttf",
        "aa52c98336f7c62e2896fc8b12b56a75d5b476d88a2f104b0980f4f7ce0adfc3",
        "91e086f4668132cd51a70ba2b6d7d9706da87f8a7f8be4b198f968ddb69894c0",
    ),
}
LICENCES = {
    "jua-OFL.txt": ("ofl/jua/OFL.txt", "44a7c6e4c5572392ae122d3b1d8c6ba6fd640a7797e675384585d947f2773e3c"),
    "gaegu-OFL.txt": ("ofl/gaegu/OFL.txt", "53a9ce47085d9fef613c7ecb3730dc80d25962510bbea231b89564f58240f251"),
}
# New frontend (docs/frontend_v2/FRONTEND_V2_PLAN.md, owner decision 2026-10-23): the three typefaces of the hand-drawn
# chalkboard draft. Not deployed until the one-time switch, when these move into FONTS and the guard pins.
# Download the extra sources the same way (ofl/blackhansans, ofl/gowundodum, ofl/nanumpenscript; save each OFL.txt under the
# V2_LICENCES name) and run with --set v2.
# output name -> (upstream path, upstream source sha256, reviewed output sha256, family name written into the subset or None)
# Nanum Pen Script carries Reserved Font Names ("Nanum", ...): a subset is a Modified Version under OFL 1.1, so it is renamed.
V2_FONTS = {
    "black-han-sans-ksx1001.woff2": (
        "ofl/blackhansans/BlackHanSans-Regular.ttf",
        "31960809284026681774a8e52dc19ebcad26cf69b0ad9d560f288296fbb52739",
        "02c5deaea5875b4d6eeb897533c717f51b91f833646ae548ac7ea4dab5102cd8",
        None,
    ),
    "gowun-dodum-ksx1001.woff2": (
        "ofl/gowundodum/GowunDodum-Regular.ttf",
        "a6e457933227483a11758fd0947bc74422a106d46f0bf057fdaa5af94a30067d",
        "67e2fb2ca3ef59df515bdac034112c0161a26f1fa1fc9b52caa0c2442ad92316",
        None,
    ),
    "is-pen-script-ksx1001.woff2": (
        "ofl/nanumpenscript/NanumPenScript-Regular.ttf",
        "6f0d1ab29c7894010dc88831fb7a0a51edb79136e450344183de5b1a8b52bd43",
        "80e706fef8eb2f9ecf8224bc0b0ceb978e40efee2fe2dc8f0880d369bbd6e682",
        "IS Pen Script",
    ),
}
V2_LICENCES = {
    "blackhansans-OFL.txt": ("ofl/blackhansans/OFL.txt", "c324192c8b3a988bae45a9a7e4ac1258b684739003bda114e0523423440457c9"),
    "gowundodum-OFL.txt": ("ofl/gowundodum/OFL.txt", "a7c73f9521cd646bbdfb6684c99a62311bbd7bce11898dc11ef0b3c69eda1aca"),
    "pen-script-OFL.txt": ("ofl/nanumpenscript/OFL.txt", "eeacf16032901d0ed0456876ec77b8f0fda6b3fecec7d972f8543eb602e6c30f"),
}
# The same ranges are the @font-face unicode-range in theme.css (checked by a test).
UNICODE_RANGE = ("U+0020-007E, U+00A0-00FF, U+2010-2027, U+2030-203A, U+20A9, U+3000-3011, U+301C, "
                 "U+3131-318E, U+AC00-D7A3, U+FF01-FF5E")


def ksx1001_hangul() -> set[int]:
    """The 2,350 KS X 1001 Hangul syllables: EUC-KR rows 0xB0-0xC8, cells 0xA1-0xFE."""
    return {ord(bytes([row, cell]).decode("euc-kr")) for row in range(0xB0, 0xC9) for cell in range(0xA1, 0xFF)}


def codepoints() -> set[int]:
    """Characters requested from each source font (kept only where the font has a glyph)."""
    wanted = set(range(0x20, 0x7F)) | set(range(0xA0, 0x100))         # Latin
    wanted |= ksx1001_hangul()                                           # KS X 1001 Hangul 2,350
    wanted |= set(range(0x3131, 0x318F))                                 # Hangul compatibility jamo
    wanted |= set(range(0x2010, 0x2028)) | set(range(0x2030, 0x203B))    # dashes, quotes, bullet, ellipsis, per mille
    wanted |= {0x20A9}                                                   # won sign
    wanted |= set(range(0x3000, 0x3012)) | {0x301C}                      # CJK punctuation and brackets
    wanted |= set(range(0xFF01, 0xFF5F))                                 # fullwidth forms
    return wanted


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rename(font, family: str) -> None:
    """Replace every family/full/PostScript name record (IDs 1, 3, 4, 6, 16, 17, 21, 22) with `family`; copyright and licence stay."""
    ps = family.replace(" ", "")
    for record in font["name"].names:
        if record.nameID in (1, 4, 16, 21):
            record.string = family
        elif record.nameID in (3, 6):
            record.string = ps + "-Regular" if record.nameID == 6 else ps + ";Regular"
        elif record.nameID in (17, 22):
            record.string = "Regular"


def subset(source: Path, target: Path, family: str | None = None) -> None:
    from fontTools import subset as ft_subset
    from fontTools.ttLib import TTFont

    font = TTFont(source, recalcTimestamp=False)  # keep the source timestamp: reproducible bytes
    cmap = font.getBestCmap()
    options = ft_subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]          # keeps the copyright (0) and licence (13, 14) name records
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.hinting = False
    options.desubroutinize = True
    subsetter = ft_subset.Subsetter(options)
    subsetter.populate(unicodes=sorted(c for c in codepoints() if c in cmap))
    subsetter.subset(font)
    if family:
        rename(font, family)
    font.flavor = "woff2"
    font.save(target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", required=True, help="directory holding the downloaded upstream files")
    parser.add_argument("--out", required=True, help="directory for the WOFF2 subsets")
    parser.add_argument("--set", choices=("current", "v2"), default="current", help="v2 = the new frontend's draft typefaces")
    args = parser.parse_args(argv)
    fonts = FONTS if args.set == "current" else {k: (u, s, o) for k, (u, s, o, _f) in V2_FONTS.items()}
    families = {} if args.set == "current" else {k: f for k, (_u, _s, _o, f) in V2_FONTS.items()}
    licences = LICENCES if args.set == "current" else V2_LICENCES
    import brotli
    import fontTools
    print(f"fontTools {fontTools.version} (recorded {FONTTOOLS_VERSION}), brotli {brotli.__version__} (recorded {BROTLI_VERSION})")
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, (upstream, digest) in licences.items():
        if _sha256(src / name) != digest:
            print(f"REFUSED {name}: not the pinned {upstream} at {UPSTREAM_COMMIT}")
            return 1
    matched = True
    for name, (upstream, source_digest, output_digest) in fonts.items():
        source = src / Path(upstream).name
        if _sha256(source) != source_digest:
            print(f"REFUSED {source.name}: not the pinned {upstream} at {UPSTREAM_COMMIT}")
            return 1
        subset(source, out / name, families.get(name))
        produced = _sha256(out / name)
        matched &= produced == output_digest
        print(f"{name} {(out / name).stat().st_size} bytes sha256 {produced} {'MATCH' if produced == output_digest else 'DIFFERS'}")
    return 0 if matched else 2


if __name__ == "__main__":
    raise SystemExit(main())
