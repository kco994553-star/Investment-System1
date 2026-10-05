"""FPIA complement-workflow analysis for AC-32.spoof (fix round 2: G1, G2; fix round 3: H1, H2).

Workflow files are read with a real YAML loader (the vendored pure-Python PyYAML: ``safe_load`` as the
validity gate, ``compose`` for the decoded scalar text, so quoting, escapes, comments, tags, block
scalars, anchors and duplicate keys are resolved as YAML resolves them). A file that is not valid YAML
for GitHub (not loadable, top level not a mapping, no jobs mapping) is "unparseable workflow
(fail-closed)".

H1 - workflow identity (fix round 3). GitHub constant expressions are folded first (``${{ 'literal' }}``
with ``''`` escapes, ``format()`` whose arguments are literals or folded expressions, nested; literals
true/false/null and decimal integers). A ``name``/``run-name`` that still contains a non-foldable
expression is FOUND fail-closed ("identity not statically determinable"). Every value is turned into
identity keys: for each of s, NFKC(s), skeleton(s), skeleton(NFKC(s)), NFKC(skeleton(s)) - casefold, then
delete every character that is not ASCII [a-z0-9]. A complement workflow claims the Track C identity if
a key of the Track C workflow's name (or run-name) or filename stem is a SUBSTRING of any key of the
workflow's name, run-name or filename stem; decorations, invisible, blank, control, combining and
punctuation characters all vanish, so equality is not needed. (Job id/name collisions stay notes,
open decision D3-b.)

Confusable source (no download at run time): the prototype table below was extracted once from the
system ICU (libicu74 74.2-1ubuntu3.1, ICU 74.2, Unicode 15.1.0 security data = UTS #39 confusables.txt)
with ``uspoof_getSkeleton`` for every NFD-stable code point, keeping every mapping whose prototype is
non-empty ASCII: 1788 code points in 297 prototype groups. Fix round 2 kept only NFKC-stable sources
(654 code points) and applied NFKC before the skeleton, which lost ICU confusables such as U+03F2 and
U+FE58 (D1); fix round 3 keeps NFKC-unstable sources too and applies the skeleton both before and after
NFKC. The Default_Ignorable ranges come from the same ICU (``u_hasBinaryProperty``
UCHAR_DEFAULT_IGNORABLE_CODE_POINT, 4174 code points). Format: ``<prototype hex code points joined by
'.'>=<source code points, comma separated>``.

H2 - what a complement workflow can run (fix round 3: a conservative over-approximation; the verdict
does not depend on resolving cd, working-directory, shell flags, wrappers or quoting). The Track C
mention set M comes from the authenticated references only: stems and basenames of the Track C tools
(the existing tool glob over R), stems of the Track C test modules, the dotted paths of every Track C
module (R's namespace modules and A_V's), the basenames of A_V paths (and stems of A_V Python files),
and the Track C workflow path/basename. Text is compared after casefolding, with every run of
non-identifier characters as a token boundary and ``. _ - /`` as joiners inside a token, so an element
matches in any hyphen/underscore/slash/dot spelling and whatever surrounds it. Every complement
workflow is scanned after YAML decoding with constant-expression folding AND as raw text (as is, with
backslash-newline and quotes removed, and with ANSI-C ``$'...'`` decoded); so is every in-tree code or
configuration file it can reach, recursively: any token that names an existing tree file (exact path,
path suffix or basename, regardless of cwd or shebang) when that file is code (a script by suffix, an
extension-less or shebang file, workflow/action YAML, build/test configuration such as *.ini, *.cfg,
*.toml, *.args); every file under a local action directory (composite, node or docker); local reusable
workflows; Makefile/makefile/GNUmakefile/*.mk when make is invoked; package.json/pyproject.toml/tox.ini/
noxfile.py when npm/yarn/pnpm/tox/nox is invoked; ``python -m`` modules mapped to tree files under any
root; pytest @argsfiles (any name) and -c ini files. Data and documents (JSON other than package.json,
Markdown, CSV, ...) are not code: a tool named only inside data read at run time is a dynamically
constructed invocation (D3-c). Any mention of M, any import of a Track C module, any glob over Track C
paths (unless it selects a whole kind of file or every test of its directories - a whole-suite
selection, recorded as a note), any path naming a Track C file (with a directory component), any pytest
-k/-m selection naming Track C tests and any pytest --ignore/--ignore-glob/--deselect that removes other
capabilities' tests while keeping Track C tests (in pytest context), and any same-repository remote
workflow/action (``uses: <this owner>/<this repo>/...@ref``, content not in T) is FOUND, unless
attributed exactly as before (a V-added workflow carrying A_V content, byte-identical to an applicable
authenticated V; never for identity claims). Files that are
byte-identical to the running FPIA verifier's own files (its directory, or Python files importing it,
at the current version or any version on the verifier checkout's history) are the auditor itself
(self-placement) and are not scanned; authenticating the verifier is open decision D3-a. The
fix-round-2 resolver (shell tokenisation, working-directory, followed scripts) still runs and its
output is kept as evidence (``resolver_reasons``) and for the whole-suite note; it never decides the
verdict. pytest over the whole suite stays a note.

Non-claims (open user decisions, current behaviour kept): dynamically constructed invocations
(string-built paths, paths in shell variables, importlib with computed names) are not claimed to be
detected (``dynamic_invocation_detection: NOT_CLAIMED``, D3-c); code that runs from outside T (remote
reusable workflows of other repositories, third-party actions, container images, installed packages)
is not analysed (``out_of_tree_code_analysis: NOT_ANALYSED``, D3-e). Job id/name collisions stay notes
(D3-b).
"""
from __future__ import annotations

import ast
import collections
import fnmatch
import posixpath
import re
import shlex
import unicodedata

try:  # vendored pure-Python PyYAML 6.0.1 (_vendor/README.md); never an installed copy
    if __package__:
        from ._vendor import yaml
    else:
        from _vendor import yaml
except ImportError:  # fail-closed: the caller reports the workflow analysis NOT_RUN
    yaml = None

try:
    from . import track_c_fpia_derive as fd
except ImportError:
    import track_c_fpia_derive as fd

DYNAMIC_INVOCATION_DETECTION = "NOT_CLAIMED"
DYNAMIC_NON_CLAIM = ("dynamically constructed invocations (string-built paths, paths held in shell variables, "
                     "importlib with computed names) are not claimed to be detected by the static spoof "
                     "analysis (open user decision D3-c)")
JOB_COLLISION_POLICY = ("a job id/name collision with the Track C workflow is recorded as a note only "
                        "(open user decision D3-b)")
OUT_OF_TREE_CODE_ANALYSIS = "NOT_ANALYSED"
OUT_OF_TREE_NOTE = ("code that runs from outside T (remote reusable workflows of other repositories, third-party "
                    "actions, container images, installed packages) is not analysed by the static spoof analysis "
                    "(out_of_tree_code_analysis: NOT_ANALYSED; open user decision D3-e, not an approved non-claim)")
MENTION_RULE = ("conservative over-approximation (fix round 3, H2): any mention of the Track C mention set M "
                "(authenticated R/A_V names) in a complement workflow or in an in-tree file it can reach is FOUND; "
                "detection does not depend on resolving cd, working-directory, shell flags, wrappers or quoting")
CONFUSABLE_SOURCE = {
    "table": "UTS #39 confusables (prototype skeleton), non-empty ASCII prototypes of NFD-stable code points "
             "(1788 code points, NFKC-unstable sources included; skeleton applied before and after NFKC)",
    "extracted_from": "ICU 74.2 (libicu74 74.2-1ubuntu3.1) uspoof_getSkeleton; Unicode 15.1.0 security data",
    "default_ignorable": "ICU 74.2 u_hasBinaryProperty(UCHAR_DEFAULT_IGNORABLE_CODE_POINT)",
    "runtime_download": False,
}

CONFUSABLES_ASCII = (
    "20=A0,1680,2002,2003,2004,2005,2006,2007,2008,2009,200A,2028,2029,202F,205F;21=1C3,2D51,FF01;21.21=2"
    "03C;21.3F=2049;26=A778;27=60,B4,2B9,2BB,2BC,2BD,2BE,2C8,2CA,2CB,2F4,384,55A,55D,5D9,5F3,7F4,7F5,144A"
    ",16CC,1FBD,1FBF,1FFE,2018,2019,201B,2032,2035,A78C,FF07,FF40,16F51,16F52;27.27=22,2BA,2DD,2EE,2F6,5F"
    "2,5F4,1CD3,201C,201D,201F,2033,2036,3003,FF02;27.27.27=2034,2037;27.27.27.27=2057;27.42=181;27.44=18"
    "A;27.50=1A4;27.54=1AC;27.59=1B3;27.6E=149;28=2768,2772,3014,FD3E,FF3B;28.28=2E28;28.32.29=2475;28.32"
    ".4F.29=2487;28.33.29=2476;28.34.29=2477;28.35.29=2478;28.36.29=2479;28.37.29=247A;28.38.29=247B;28.3"
    "9.29=247C;28.41.29=1F110;28.42.29=1F111;28.43.29=1F112;28.44.29=1F113;28.45.29=1F114;28.46.29=1F115;"
    "28.47.29=1F116;28.48.29=1F117;28.4A.29=1F119;28.4B.29=1F11A;28.4C.29=1F11B;28.4D.29=1F11C;28.4E.29=1"
    "F11D;28.4F.29=1F11E;28.50.29=1F11F;28.51.29=1F120;28.52.29=1F121;28.53.29=1F122,1F12A;28.54.29=1F123"
    ";28.55.29=1F124;28.56.29=1F125;28.57.29=1F126;28.58.29=1F127;28.59.29=1F128;28.5A.29=1F129;28.61.29="
    "249C;28.62.29=249D;28.63.29=249E;28.64.29=249F;28.65.29=24A0;28.66.29=24A1;28.67.29=24A2;28.68.29=24"
    "A3;28.69.29=24A4;28.6A.29=24A5;28.6B.29=24A6;28.6C.29=2474,24A7,1F118;28.6C.32.29=247F;28.6C.33.29=2"
    "480;28.6C.34.29=2481;28.6C.35.29=2482;28.6C.36.29=2483;28.6C.37.29=2484;28.6C.38.29=2485;28.6C.39.29"
    "=2486;28.6C.4F.29=247D;28.6C.6C.29=247E;28.6E.29=24A9;28.6F.29=24AA;28.70.29=24AB;28.71.29=24AC;28.7"
    "2.29=24AD;28.72.6E.29=24A8;28.73.29=24AE;28.74.29=24AF;28.75.29=24B0;28.76.29=24B1;28.77.29=24B2;28."
    "78.29=24B3;28.79.29=24B4;28.7A.29=24B5;29=2769,2773,3015,FD3F,FF3D;29.29=2E29;2A=66D,204E,2217,1031F"
    ";2B=16ED,2795,1029B;2C=B8,60D,66B,201A,A4F9;2D=2D7,6D4,2010,2011,2012,2013,2043,2212,2796,2CBA,FE58;"
    "2D.2E=A4FE;2E=660,6F0,701,702,2024,A4F8,A60E,10A50,1D16D;2E.2C=A4FB;2E.2E=2025,A4FA;2E.2E.2E=2026;2F"
    "=1735,2041,2044,2215,2571,27CB,29F8,2CC6,2F03,3033,30CE,31D3,4E3F,1D23A;2F.2F=2AFD;2F.2F.2F=2AFB;32="
    "1A7,3E8,14BF,A644,A6EF,A75A,1D7D0,1D7DA,1D7E4,1D7EE,1D7F8,1FBF2;32.2C=1F103;32.2E=2489;32.4F.2E=249B"
    ";33=1B7,21C,417,4E0,2CCC,A76A,A7AB,118CA,16F3B,1D206,1D7D1,1D7DB,1D7E5,1D7EF,1D7F9,1FBF3;33.2C=1F104"
    ";33.2E=248A;34=13CE,118AF,1D7D2,1D7DC,1D7E6,1D7F0,1D7FA,1FBF4;34.2C=1F105;34.2E=248B;35=1BC,118BB,1D"
    "7D3,1D7DD,1D7E7,1D7F1,1D7FB,1FBF5;35.2C=1F106;35.2E=248C;36=431,13EE,2CD2,118D5,1D7D4,1D7DE,1D7E8,1D"
    "7F2,1D7FC,1FBF6;36.2C=1F107;36.2E=248D;37=104D2,118C6,1D212,1D7D5,1D7DF,1D7E9,1D7F3,1D7FD,1FBF7;37.2"
    "C=1F108;37.2E=248E;38=222,223,9EA,A6A,B03,1031A,1D7D6,1D7E0,1D7EA,1D7F4,1D7FE,1E8CB,1FBF8;38.2C=1F10"
    "9;38.2E=248F;39=9ED,A67,B68,D6D,2CCA,A76E,118AC,118CC,118D6,1D7D7,1D7E1,1D7EB,1D7F5,1D7FF,1FBF9;39.2"
    "C=1F10A;39.2E=2490;3A=2D0,2F8,589,5C3,703,704,903,A83,16EC,1803,1809,205A,2236,A4FD,A789,FE30,FF1A;3"
    "A.3A.3D=2A74;3C=2C2,1438,16B2,2039,276E,1D236;3C.3C=226A;3C.3C.3C=22D8;3D=1400,2E40,30A0,A4FF;3D.3D="
    "2A75;3D.3D.3D=2A76;3E=2C3,1433,203A,276F,16F3F,1D237;3E.3C=2AA5;3E.3E=226B,2A20;3E.3E.3E=22D9;3F=241"
    ",294,97D,13AE,A6EB;3F.21=2048;3F.3F=2047;41=391,410,13AA,15C5,A4EE,FF21,102A0,16F40,1D400,1D434,1D46"
    "8,1D49C,1D4D0,1D504,1D538,1D56C,1D5A0,1D5D4,1D608,1D63C,1D670,1D6A8,1D6E2,1D71C,1D756,1D790;41.41=A7"
    "32;41.45=C6,4D4;41.4F=A734;41.52=1F707;41.55=A736;41.56=A738,A73A;41.59=A73C;42=392,412,13F4,15F7,21"
    "2C,A4D0,A7B4,FF22,10282,102A1,10301,1D401,1D435,1D469,1D4D1,1D505,1D539,1D56D,1D5A1,1D5D5,1D609,1D63"
    "D,1D671,1D6A9,1D6E3,1D71D,1D757,1D791;43=3F9,421,13DF,2102,212D,216D,2CA4,A4DA,FF23,102A2,10302,1041"
    "5,1051C,118E9,118F2,1D402,1D436,1D46A,1D49E,1D4D2,1D56E,1D5A2,1D5D6,1D60A,1D63E,1D672,1F74C;43.27=18"
    "7;44=13A0,15DE,15EA,2145,216E,A4D3,1D403,1D437,1D46B,1D49F,1D4D3,1D507,1D53B,1D56F,1D5A3,1D5D7,1D60B"
    ",1D63F,1D673;44.5A=1F1;44.7A=1F2;45=395,415,13AC,2130,22FF,2D39,A4F0,FF25,10286,118A6,118AE,1D404,1D"
    "438,1D46C,1D4D4,1D508,1D53C,1D570,1D5A4,1D5D8,1D60C,1D640,1D674,1D6AC,1D6E6,1D720,1D75A,1D794;46=3DC"
    ",15B4,2131,A4DD,A798,10287,102A5,10525,118A2,118C2,1D213,1D405,1D439,1D46D,1D4D5,1D509,1D53D,1D571,1"
    "D5A5,1D5D9,1D60D,1D641,1D675,1D7CA;46.41.58=213B;47=50C,13C0,13F3,A4D6,1D406,1D43A,1D46E,1D4A2,1D4D6"
    ",1D50A,1D53E,1D572,1D5A6,1D5DA,1D60E,1D642,1D676;47.27=193;48=397,41D,13BB,157C,210B,210C,210D,2C8E,"
    "A4E7,FF28,102CF,1D407,1D43B,1D46F,1D4D7,1D573,1D5A7,1D5DB,1D60F,1D643,1D677,1D6AE,1D6E8,1D722,1D75C,"
    "1D796;4A=37F,408,13AB,148D,A4D9,A7B2,FF2A,1D409,1D43D,1D471,1D4A5,1D4D9,1D50D,1D541,1D575,1D5A9,1D5D"
    "D,1D611,1D645,1D679;4B=39A,41A,13E6,16D5,2C94,A4D7,FF2B,10518,1D40A,1D43E,1D472,1D4A6,1D4DA,1D50E,1D"
    "542,1D576,1D5AA,1D5DE,1D612,1D646,1D67A,1D6B1,1D6EB,1D725,1D75F,1D799;4B.27=198;4C=13DE,14AA,2112,21"
    "6C,2CD0,A4E1,1041B,10526,118A3,118B2,16F16,1D22A,1D40B,1D43F,1D473,1D4DB,1D50F,1D543,1D577,1D5AB,1D5"
    "DF,1D613,1D647,1D67B;4C.4A=1C7;4C.6A=1C8;4D=39C,3FA,41C,13B7,15F0,16D6,2133,216F,2C98,A4DF,FF2D,102B"
    "0,10311,1D40C,1D440,1D474,1D4DC,1D510,1D544,1D578,1D5AC,1D5E0,1D614,1D648,1D67C,1D6B3,1D6ED,1D727,1D"
    "761,1D79B;4D.42=1F76B;4E=39D,2115,2C9A,A4E0,FF2E,10513,1D40D,1D441,1D475,1D4A9,1D4DD,1D511,1D579,1D5"
    "AD,1D5E1,1D615,1D649,1D67D,1D6B4,1D6EE,1D728,1D762,1D79C;4E.4A=1CA;4E.6A=1CB;4E.6F=2116;4F=30,39F,41"
    "E,555,7C0,9E6,B20,B66,12D0,2C9E,2D54,3007,A4F3,FF2F,10292,102AB,10404,104C2,10516,114D0,118B5,118E0,"
    "1D40E,1D442,1D476,1D4AA,1D4DE,1D512,1D546,1D57A,1D5AE,1D5E2,1D616,1D64A,1D67E,1D6B6,1D6F0,1D72A,1D76"
    "4,1D79E,1D7CE,1D7D8,1D7E2,1D7EC,1D7F6,1FBF0;4F.27=13A4;4F.2C=1F101;4F.2E=1F100;4F.45=152;4F.4F=A698,"
    "A74E;50=3A1,420,13E2,146D,2119,2CA2,A4D1,FF30,10295,1D40F,1D443,1D477,1D4AB,1D4DF,1D513,1D57B,1D5AF,"
    "1D5E3,1D617,1D64B,1D67F,1D6B8,1D6F2,1D72C,1D766,1D7A0;50.27=1486;51=211A,2D55,1D410,1D444,1D478,1D4A"
    "C,1D4E0,1D514,1D57C,1D5B0,1D5E4,1D618,1D64C,1D680;51.45=1F700;52=1A6,13A1,13D2,1587,211B,211C,211D,A"
    "4E3,104B4,16F35,1D216,1D411,1D445,1D479,1D4E1,1D57D,1D5B1,1D5E5,1D619,1D64D,1D681;52.73=20A8;53=405,"
    "54F,13D5,13DA,A4E2,FF33,10296,10420,16F3A,1D412,1D446,1D47A,1D4AE,1D4E2,1D516,1D54A,1D57E,1D5B2,1D5E"
    "6,1D61A,1D64E,1D682;54=3A4,422,13A2,22A4,27D9,2CA6,A4D4,FF34,10297,102B1,10315,118BC,16F0A,1D413,1D4"
    "47,1D47B,1D4AF,1D4E3,1D517,1D54B,1D57F,1D5B3,1D5E7,1D61B,1D64F,1D683,1D6BB,1D6F5,1D72F,1D769,1D7A3,1"
    "F768;54.33=A728;54.45.4C=2121;55=54D,1200,144C,222A,22C3,A4F4,104CE,118B8,16F42,1D414,1D448,1D47C,1D"
    "4B0,1D4E4,1D518,1D54C,1D580,1D5B4,1D5E8,1D61C,1D650,1D684;55.27=1467;56=474,667,6F7,13D9,142F,2164,2"
    "D38,A4E6,A6DF,1051D,118A0,16F08,1D20D,1D415,1D449,1D47D,1D4B1,1D4E5,1D519,1D54D,1D581,1D5B5,1D5E9,1D"
    "61D,1D651,1D685;56.42=1F76C;56.6C=2165;56.6C.6C=2166;56.6C.6C.6C=2167;57=51C,13B3,13D4,A4EA,118E6,11"
    "8EF,1D416,1D44A,1D47E,1D4B2,1D4E6,1D51A,1D54E,1D582,1D5B6,1D5EA,1D61E,1D652,1D686;58=3A7,425,166D,16"
    "B7,2169,2573,2CAC,2D5D,A4EB,A7B3,FF38,10290,102B4,10317,10322,10527,118EC,1D417,1D44B,1D47F,1D4B3,1D"
    "4E7,1D51B,1D54F,1D583,1D5B7,1D5EB,1D61F,1D653,1D687,1D6BE,1D6F8,1D732,1D76C,1D7A6;58.6C=216A;58.6C.6"
    "C=216B;59=3A5,3D2,423,4AE,13A9,13BD,2CA8,A4EC,FF39,102B2,118A4,16F43,1D418,1D44C,1D480,1D4B4,1D4E8,1"
    "D51C,1D550,1D584,1D5B8,1D5EC,1D620,1D654,1D688,1D6BC,1D6F6,1D730,1D76A,1D7A4;5A=396,13C3,2124,2128,A"
    "4DC,FF3A,102F5,118A9,118E5,1D419,1D44D,1D481,1D4B5,1D4E9,1D585,1D5B9,1D5ED,1D621,1D655,1D689,1D6AD,1"
    "D6E7,1D721,1D75B,1D795;5C=2216,27CD,29F5,29F9,2F02,31D4,4E36,FE68,FF3C,1D20F,1D23B;5C.5C=244A,2CF9;5"
    "E=2C4,2C6;5F=7FA,FE4D,FE4E,FE4F;61=251,3B1,430,237A,FF41,1D41A,1D44E,1D482,1D4B6,1D4EA,1D51E,1D552,1"
    "D586,1D5BA,1D5EE,1D622,1D656,1D68A,1D6C2,1D6FC,1D736,1D770,1D7AA;61.2F.63=2100;61.2F.73=2101;61.61=A"
    "733;61.65=E6,4D5;61.6F=A735;61.75=A737;61.76=A739,A73B;61.79=A73D;62=184,42C,13CF,1472,15AF,1D41B,1D"
    "44F,1D483,1D4B7,1D4EB,1D51F,1D553,1D587,1D5BB,1D5EF,1D623,1D657,1D68B;62.27=1488;62.6C=42B;63=3F2,44"
    "1,1D04,217D,2CA5,ABAF,FF43,1043D,1D41C,1D450,1D484,1D4B8,1D4EC,1D520,1D554,1D588,1D5BC,1D5F0,1D624,1"
    "D658,1D68C;63.2F.6F=2105;63.2F.75=2106;64=501,13E7,146F,2146,217E,A4D2,1D41D,1D451,1D485,1D4B9,1D4ED"
    ",1D521,1D555,1D589,1D5BD,1D5F1,1D625,1D659,1D68D;64.27=1487;64.7A=1F3,2A3;65=435,4BD,212E,212F,2147,"
    "AB32,FF45,1D41E,1D452,1D486,1D4EE,1D522,1D556,1D58A,1D5BE,1D5F2,1D626,1D65A,1D68E;66=17F,584,1E9D,A7"
    "99,AB35,1D41F,1D453,1D487,1D4BB,1D4EF,1D523,1D557,1D58B,1D5BF,1D5F3,1D627,1D65B,1D68F;66.66=FB00;66."
    "66.69=FB03;66.66.6C=FB04;66.69=FB01;66.6C=FB02;67=18D,261,581,1D83,210A,FF47,1D420,1D454,1D488,1D4F0"
    ",1D524,1D558,1D58C,1D5C0,1D5F4,1D628,1D65C,1D690;68=4BB,570,13C2,210E,FF48,1D421,1D489,1D4BD,1D4F1,1"
    "D525,1D559,1D58D,1D5C1,1D5F5,1D629,1D65D,1D691;69=131,269,26A,2DB,37A,3B9,456,4CF,13A5,2139,2148,217"
    "0,2373,A647,AB75,FF49,118C3,1D422,1D456,1D48A,1D4BE,1D4F2,1D526,1D55A,1D58E,1D5C2,1D5F6,1D62A,1D65E,"
    "1D692,1D6A4,1D6CA,1D704,1D73E,1D778,1D7B2;69.69=2171;69.69.69=2172;69.6A=133;69.76=2173;69.78=2178;6"
    "A=3F3,458,2149,FF4A,1D423,1D457,1D48B,1D4BF,1D4F3,1D527,1D55B,1D58F,1D5C3,1D5F7,1D62B,1D65F,1D693;6B"
    "=1D424,1D458,1D48C,1D4C0,1D4F4,1D528,1D55C,1D590,1D5C4,1D5F8,1D62C,1D660,1D694;6C=31,49,7C,196,1C0,3"
    "99,406,4C0,5C0,5D5,5DF,627,661,6F1,7CA,16C1,2110,2111,2113,2160,217C,2223,23FD,2C92,2D4F,A4F2,FE8D,F"
    "E8E,FF29,FF4C,FFE8,1028A,10309,10320,16F28,1D408,1D425,1D43C,1D459,1D470,1D48D,1D4C1,1D4D8,1D4F5,1D5"
    "29,1D540,1D55D,1D574,1D591,1D5A8,1D5C5,1D5DC,1D5F9,1D610,1D62D,1D644,1D661,1D678,1D695,1D6B0,1D6EA,1"
    "D724,1D75E,1D798,1D7CF,1D7D9,1D7E3,1D7ED,1D7F7,1E8C7,1EE00,1EE80,1FBF1;6C.27=5F1;6C.2C=1F102;6C.2E=2"
    "488;6C.32.2E=2493;6C.33.2E=2494;6C.34.2E=2495;6C.35.2E=2496;6C.36.2E=2497;6C.37.2E=2498;6C.38.2E=249"
    "9;6C.39.2E=249A;6C.4A=132;6C.4F=42E;6C.4F.2E=2491;6C.56=2163;6C.58=2168;6C.6A=1C9;6C.6C=1C1,5F0,2016"
    ",2161,2225;6C.6C.2E=2492;6C.6C.6C=2162;6C.73=2AA;6C.74=20B6;6C.7A=2AB;6E=578,57C,1D427,1D45B,1D48F,1"
    "D4C3,1D4F7,1D52B,1D55F,1D593,1D5C7,1D5FB,1D62F,1D663,1D697;6E.6A=1CC;6F=3BF,3C3,43E,585,5E1,647,665,"
    "6BE,6C1,6D5,6F5,966,A66,AE6,BE6,C02,C66,C82,CE6,D02,D20,D66,D82,E50,ED0,101D,1040,10FF,1D0F,1D11,213"
    "4,2C9F,AB3D,FBA6,FBA7,FBA8,FBA9,FBAA,FBAB,FBAC,FBAD,FEE9,FEEA,FEEB,FEEC,FF4F,1042C,104EA,118C8,118D7"
    ",1D428,1D45C,1D490,1D4F8,1D52C,1D560,1D594,1D5C8,1D5FC,1D630,1D664,1D698,1D6D0,1D6D4,1D70A,1D70E,1D7"
    "44,1D748,1D77E,1D782,1D7B8,1D7BC,1EE24,1EE64,1EE84;6F.65=153;6F.6F=221E,A699,A74F;70=3C1,3F1,440,237"
    "4,2CA3,FF50,1D429,1D45D,1D491,1D4C5,1D4F9,1D52D,1D561,1D595,1D5C9,1D5FD,1D631,1D665,1D699,1D6D2,1D6E"
    "0,1D70C,1D71A,1D746,1D754,1D780,1D78E,1D7BA,1D7C8;71=51B,563,566,1D42A,1D45E,1D492,1D4C6,1D4FA,1D52E"
    ",1D562,1D596,1D5CA,1D5FE,1D632,1D666,1D69A;72=433,1D26,2C85,AB47,AB48,AB81,1D42B,1D45F,1D493,1D4C7,1"
    "D4FB,1D52F,1D563,1D597,1D5CB,1D5FF,1D633,1D667,1D69B;72.27=491;72.6E=6D,217F,11700,118E3,1D426,1D45A"
    ",1D48E,1D4C2,1D4F6,1D52A,1D55E,1D592,1D5C6,1D5FA,1D62E,1D662,1D696;73=1BD,455,A731,ABAA,FF53,10448,1"
    "18C1,1D42C,1D460,1D494,1D4C8,1D4FC,1D530,1D564,1D598,1D5CC,1D600,1D634,1D668,1D69C;73.73.73=1F75C;73"
    ".74=FB06;74=1D42D,1D461,1D495,1D4C9,1D4FD,1D531,1D565,1D599,1D5CD,1D601,1D635,1D669,1D69D;74.66=A777"
    ";74.73=2A6;75=28B,3C5,57D,1D1C,A79F,AB4E,AB52,104F6,118D8,1D42E,1D462,1D496,1D4CA,1D4FE,1D532,1D566,"
    "1D59A,1D5CE,1D602,1D636,1D66A,1D69E,1D6D6,1D710,1D74A,1D784,1D7BE;75.65=1D6B;75.6F=AB63;76=3BD,475,5"
    "D8,1D20,2174,2228,22C1,ABA9,FF56,11706,118C0,1D42F,1D463,1D497,1D4CB,1D4FF,1D533,1D567,1D59B,1D5CF,1"
    "D603,1D637,1D66B,1D69F,1D6CE,1D708,1D742,1D77C,1D7B6;76.69=2175;76.69.69=2176;76.69.69.69=2177;77=26"
    "F,461,51D,561,1D21,AB83,1170A,1170E,1170F,1D430,1D464,1D498,1D4CC,1D500,1D534,1D568,1D59C,1D5D0,1D60"
    "4,1D638,1D66C,1D6A0;78=D7,445,1541,157D,166E,2179,292B,292C,2A2F,FF58,1D431,1D465,1D499,1D4CD,1D501,"
    "1D535,1D569,1D59D,1D5D1,1D605,1D639,1D66D,1D6A1;78.69=217A;78.69.69=217B;79=263,28F,3B3,443,4AF,10E7"
    ",1D8C,1EFF,213D,AB5A,FF59,118DC,1D432,1D466,1D49A,1D4CE,1D502,1D536,1D56A,1D59E,1D5D2,1D606,1D63A,1D"
    "66E,1D6A2,1D6C4,1D6FE,1D738,1D772,1D7AC;7A=1D22,AB93,118C4,1D433,1D467,1D49B,1D4CF,1D503,1D537,1D56B"
    ",1D59F,1D5D3,1D607,1D63B,1D66F,1D6A3;7B=2774,1D114;7D=2775;7E=2DC,1FC0,2053,223C"
)
DEFAULT_IGNORABLE = "AD-AD;34F-34F;61C-61C;115F-1160;17B4-17B5;180B-180F;200B-200F;202A-202E;2060-206F;3164-3164;FE00-FE0F;FEFF-FEFF;FFA0-FFA0;FFF0-FFF8;1BCA0-1BCA3;1D173-1D17A;E0000-E0FFF"


def _table():
    out = {}
    for group in CONFUSABLES_ASCII.split(";"):
        proto, _, srcs = group.partition("=")
        target = "".join(chr(int(x, 16)) for x in proto.split("."))
        for s in srcs.split(","):
            out[chr(int(s, 16))] = target
    return out


def _ranges():
    out = []
    for item in DEFAULT_IGNORABLE.split(";"):
        a, _, b = item.partition("-")
        out.append((int(a, 16), int(b, 16)))
    return out


_PROTO = _table()
_DI = _ranges()


def is_default_ignorable(ch):
    cp = ord(ch)
    return any(a <= cp <= b for a, b in _DI)


def strip_ignorable(s):
    return "".join(ch for ch in s if not is_default_ignorable(ch))


def skeleton(s):
    """UTS #39 skeleton over the embedded ASCII-prototype table: NFD, map, NFD."""
    d = unicodedata.normalize("NFD", s)
    return unicodedata.normalize("NFD", "".join(_PROTO.get(ch, ch) for ch in d))


def normal_forms(s):
    """(N1, N2) - see the module docstring."""
    s = unicodedata.normalize("NFKC", s or "")
    n1 = skeleton(strip_ignorable(unicodedata.normalize("NFKC", s.casefold()))).strip()
    n2 = unicodedata.normalize("NFKC", skeleton(strip_ignorable(s)).casefold()).strip()
    return n1, n2


def same_name(a, b):
    """Raw equality or equality of either normal form."""
    if a is None or b is None:
        return None
    if a == b:
        return "exact"
    fa, fb = normal_forms(a), normal_forms(b)
    if fa[0] and fa[0] == fb[0]:
        return "N1"
    if fa[1] and fa[1] == fb[1]:
        return "N2"
    return None


def stem(path):
    base = path.rsplit("/", 1)[-1]
    for ext in (".yml", ".yaml"):
        if base.casefold().endswith(ext):
            return base[:-len(ext)]
    return base


def is_workflow_path(p):
    return p.startswith(fd.WORKFLOW_DIR) and p.casefold().endswith((".yml", ".yaml"))


# ---- YAML ------------------------------------------------------------------------------------------
class LoaderUnavailable(Exception):
    """PyYAML is not importable: the workflow analysis is NOT_RUN (never PASS)."""


class Unparseable(Exception):
    """Not valid YAML for GitHub."""


def loader_info():
    if yaml is None:
        return None
    return {"module": "yaml", "version": getattr(yaml, "__version__", None), "source": "vendored (_vendor/yaml)",
            "with_libyaml": getattr(yaml, "__with_libyaml__", None),
            "validity_gate": "yaml.safe_load", "composer": "yaml.compose(Loader=yaml.SafeLoader) (pure Python)"}


def load(data):
    """Root node of a workflow/action file. ``data`` is bytes or str."""
    if yaml is None:
        raise LoaderUnavailable("PyYAML is not importable")
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Unparseable("not UTF-8: %s" % exc)
    try:
        yaml.safe_load(data)
        node = yaml.compose(data, Loader=yaml.SafeLoader)
    except (yaml.YAMLError, ValueError, TypeError, RecursionError) as exc:
        raise Unparseable(str(exc).replace("\n", " ")[-300:])
    if node is None or not isinstance(node, yaml.MappingNode):
        raise Unparseable("top level is not a mapping")
    return node


def _items(node, seen=None):
    """(key, value-node) pairs of a mapping node, with duplicate keys kept and merge keys followed."""
    if yaml is None or not isinstance(node, yaml.MappingNode):
        return []
    seen = set() if seen is None else seen
    if id(node) in seen:
        return []
    seen.add(id(node))
    out = []
    for k, v in node.value:
        if isinstance(k, yaml.ScalarNode) and k.tag == "tag:yaml.org,2002:merge":
            for m in (v.value if isinstance(v, yaml.SequenceNode) else [v]):
                out.extend(_items(m, seen))
            continue
        out.append((k.value if isinstance(k, yaml.ScalarNode) else None, v))
    return out


def get_all(node, key):
    return [v for k, v in _items(node) if k == key]


def scalars(node, key=None):
    return [v.value for v in (get_all(node, key) if key is not None else [node])
            if yaml is not None and isinstance(v, yaml.ScalarNode)]


def seq(node):
    return list(node.value) if yaml is not None and isinstance(node, yaml.SequenceNode) else []


def all_scalars(node, seen=None):
    """Every decoded scalar (keys and values) of a node tree."""
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return []
    seen.add(id(node))
    if isinstance(node, yaml.ScalarNode):
        return [node.value]
    out = []
    if isinstance(node, yaml.SequenceNode):
        for v in node.value:
            out += all_scalars(v, seen)
    elif isinstance(node, yaml.MappingNode):
        for k, v in node.value:
            out += all_scalars(k, seen) + all_scalars(v, seen)
    return out


def default_wd(node):
    """defaults.run.working-directory of a workflow or job node (None if absent)."""
    for d in get_all(node, "defaults"):
        for r in get_all(d, "run"):
            vals = scalars(r, "working-directory")
            if vals:
                return vals[-1]
    return None


def identity(root):
    """Names and job ids/names of a workflow root node; raises Unparseable without a jobs mapping."""
    names = scalars(root, "name") + scalars(root, "run-name")
    jobs = []
    for jn in get_all(root, "jobs"):
        for jid, job in _items(jn):
            if jid is not None:
                jobs.append((jid, job))
    if not jobs:
        raise Unparseable("no jobs mapping")
    job_names = [n for _, job in jobs for n in scalars(job, "name")]
    return {"names": names, "job_ids": [j for j, _ in jobs], "job_names": job_names, "jobs": jobs}


# ---- reference resolution ----------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[A-Za-z0-9_./*?\[\]-]+")
WORKSPACE_PREFIXES = ("${{ github.workspace }}/", "${{github.workspace}}/", "$GITHUB_WORKSPACE/",
                      "${GITHUB_WORKSPACE}/")
PYTHON_RE = re.compile(r"^(?:.*/)?python(?:[0-9.]*)$")
SHELLS = ("bash", "sh", "dash", "zsh", "ksh")
WRAPPERS = ("env", "time", "exec", "nohup", "command", "sudo", "xvfb-run")
OPERATORS = {"&&", "||", ";", "|", "&", "(", ")", ";;", "|&", "!", "{", "}"}
PYTEST_VALUE_SHORT = "kmpcoWrn"
PYTEST_VALUE_LONG = {"--deselect", "--ignore", "--ignore-glob", "--rootdir", "--junitxml", "--junit-xml",
                     "--junit-prefix", "--basetemp", "--confcutdir", "--tb", "--color", "--durations",
                     "--durations-min", "--maxfail", "--import-mode", "--log-level", "--log-file",
                     "--log-format", "--log-date-format", "--log-cli-level", "--log-cli-format",
                     "--log-file-level", "--log-file-format", "--capture", "--override-ini", "--cov",
                     "--cov-report", "--cov-config", "--timeout", "--dist", "--pythonwarnings", "--config-file"}
PYTHON_VALUE_OPTS = ("-W", "-X", "--check-hash-based-pycs")


def _norm(path):
    p = posixpath.normpath(path)
    if p in (".", "") or p.startswith("../") or p == ".." or p.startswith("/"):
        return None
    return p


WORKSPACE_EXPR = re.compile(r"\$\{\{\s*github\.workspace\s*\}\}")


def _subst(text):
    """GitHub substitutes ``${{ github.workspace }}`` before the shell runs; it names the repository root."""
    return WORKSPACE_EXPR.sub("$GITHUB_WORKSPACE", text)


def _strip_workspace(token):
    for pre in WORKSPACE_PREFIXES:
        if token.startswith(pre):
            return token[len(pre):], True
    return token, False


def resolve(token, bases):
    """Repository-relative candidate paths of a token (absolute and unresolvable tokens give none)."""
    token, rooted = _strip_workspace(token)
    if not token or token.startswith(("/", "~", "$")) or "://" in token:
        return set()
    out = set()
    for base in ([""] if rooted else bases):
        p = _norm((base.rstrip("/") + "/" + token) if base else token)
        if p:
            out.add(p)
    return out


class Analysis:
    """One complement workflow file: reasons (spoof conditions), notes and A_V references."""

    def __init__(self, ctx, path):
        self.ctx, self.path = ctx, path
        self.reasons, self.notes = [], []
        self.references = set()
        self._categories = set()
        self.av_ref = None
        self.visited = set()
        self.followed = []

    def reason(self, text, category=None, ref=None):
        """Record a spoof condition. With ``category`` only its first occurrence becomes a reason (as the
        pre-fix-round-2 rule did); every hit is kept in ``references``."""
        if ref is not None:
            self.references.add("%s: %s" % (category or text, ref))
        if category is not None:
            if category in self._categories:
                return
            self._categories.add(category)
        if text not in self.reasons:
            self.reasons.append(text)

    def whole_kind(self, rx, pattern):
        """True when the glob matches every tree file with its literal suffix (``*.py``, ``**/*.py``): it
        selects a whole kind of file, not Track C files."""
        last = pattern.rsplit("/", 1)[-1]
        if "." not in last:
            return False
        suffix = "." + last.rsplit(".", 1)[-1]
        if any(ch in suffix for ch in _GLOB_CHARS):
            return False
        same = [f for f in self.ctx.sorted_files if f.endswith(suffix)]
        return bool(same) and all(rx.match(f) for f in same)

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    # -- generic token scan (the pre-existing rule, applied to decoded text with resolved bases) --------
    def scan_text(self, text, bases, where):
        ctx = self.ctx
        text = _subst(text)
        tokens = set(TOKEN_RE.findall(text))
        try:
            words = shlex.split(text, comments=False)
        except ValueError:
            words = []
        for w in words:
            tokens.update(TOKEN_RE.findall(w))
            w2, rooted = _strip_workspace(w)
            if rooted and TOKEN_RE.fullmatch(w2):
                tokens.add("$GITHUB_WORKSPACE/" + w2)
        for token in sorted(tokens):
            stripped, rooted = _strip_workspace(token)
            if "/" not in stripped and not stripped.endswith(".py"):
                continue
            cands = resolve(token, sorted(set(bases) | {"", fd.IMPL}))
            if any(c in ctx.av for c in cands):
                self.av_ref = self.av_ref or stripped
                self.reason("references an A_V path: " + stripped, "av", stripped)
                continue
            plain = [c for c in cands if not any(ch in c for ch in "*?[")]
            if any(ctx.ns(c) and not stripped.endswith("/") for c in plain):
                self.reason("references a Track C namespace path: " + stripped + where, "ns", stripped + where)
            elif any(ch in stripped for ch in "*?["):
                hit = [q for q in ctx.ns_paths if any(fnmatch.fnmatchcase(q, c) for c in cands)]
                if hit:
                    self.reason("glob matches Track C paths: " + stripped + where, "glob", stripped + where)

    # -- shell ---------------------------------------------------------------------------------------
    def shell(self, text, cwd, bases, where, shell_name=None):
        if shell_name and PYTHON_RE.match(shell_name.split()[0] if shell_name.split() else ""):
            self.python_source(text.encode(), None, cwd, bases, where)
            return
        text = _subst(text)
        self.scan_text(text, bases, where)
        lines = text.replace("\\\n", " ").split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            i += 1
            heredoc = None
            m = re.search(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2", line)
            if m:
                body = []
                while i < len(lines) and (lines[i].lstrip("\t") if m.group(1) else lines[i]) != m.group(3):
                    body.append(lines[i])
                    i += 1
                i += 1
                heredoc = "\n".join(body)
                line = line[:m.start()] + line[m.end():]
            for words in self.commands(line):
                cwd = self.command(words, cwd, bases, where, heredoc)

    @staticmethod
    def commands(line):
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        try:
            toks = list(lex)
        except ValueError:
            return []
        out, cur = [], []
        for t in toks:
            if t in OPERATORS or set(t) <= set("&|;()<>"):
                if cur:
                    out.append(cur)
                cur = [] if t not in ("<", ">", ">>", "2>", "&>") else cur
                continue
            cur.append(t)
        if cur:
            out.append(cur)
        return out

    def command(self, words, cwd, bases, where, heredoc=None):
        words = _launch_words(words)
        if not words:
            return cwd
        self.scan_text(" ".join(shlex.quote(w) for w in words), sorted(set(bases) | {cwd}), where)
        cmd = words[0]
        if cmd == "cd":
            if len(words) > 1 and "$" not in words[1]:
                d = resolve(words[1], [cwd])
                return sorted(d)[0] if d else cwd
            return cwd
        if PYTHON_RE.match(cmd):
            self.python_cmd(words[1:], cwd, bases, where, heredoc)
        elif cmd in ("pytest", "py.test"):
            self.pytest(words[1:], cwd, where)
        elif cmd in SHELLS or cmd in ("source", "."):
            args = words[1:]
            while args and args[0].startswith("-"):
                if args[0] == "-c" and len(args) > 1:
                    self.shell(args[1], cwd, bases, where)
                    return cwd
                args.pop(0)
            if args:
                self.follow(args[0], cwd, bases, "shell", where)
            elif heredoc is not None:
                self.shell(heredoc, cwd, bases, where)
        elif "/" in cmd:
            self.follow(cmd, cwd, bases, None, where)
        return cwd

    def python_cmd(self, args, cwd, bases, where, heredoc=None):
        args = list(args)
        while args and args[0].startswith("-") and args[0] not in ("-m", "-c", "-"):
            opt = args.pop(0)
            if opt in PYTHON_VALUE_OPTS and args:
                args.pop(0)
        if not args:
            return
        if args[0] == "-m" and len(args) > 1:
            mod = args[1]
            if mod == "pytest":
                self.pytest(args[2:], cwd, where)
                return
            rel = mod.replace(".", "/")
            for cand in ([rel + ".py", rel + "/__main__.py"]):
                for p in sorted(resolve(cand, sorted({cwd, fd.IMPL, fd.IMPL + "/src", ""}))):
                    if p in self.ctx.files:
                        self.script(p, cwd, bases, "python", where)
            return
        if args[0] == "-c" and len(args) > 1:
            self.python_source(args[1].encode(), None, cwd, bases, where)
            return
        if args[0] == "-":
            if heredoc is not None:
                self.python_source(heredoc.encode(), None, cwd, bases, where)
            return
        self.follow(args[0], cwd, bases, "python", where)

    def follow(self, token, cwd, bases, kind, where):
        for p in sorted(resolve(token, [cwd])):
            if p in self.ctx.files:
                self.script(p, cwd, bases, kind, where)

    def script(self, p, cwd, bases, kind, where):
        ctx = self.ctx
        if p in ctx.av:
            self.av_ref = self.av_ref or p
            self.reason("references an A_V path: " + p, "av", p)
            return
        if ctx.ns(p):
            self.reason("runs a Track C tool or module: " + p + where, "runs", p + where)
            return
        if kind is None:
            first = ctx.read(p).split(b"\n", 1)[0]
            if p.endswith((".sh", ".bash")):
                kind = "shell"
            elif p.endswith(".py"):
                kind = "python"
            elif first.startswith(b"#!"):
                kind = "python" if b"python" in first else "shell"
            else:
                return
        if p in self.visited:
            return
        self.visited.add(p)
        self.followed.append(p)
        data = ctx.read(p)
        sbases = sorted(set(bases) | {cwd, posixpath.dirname(p)})
        w = " (via %s)" % p
        if kind == "python":
            self.python_source(data, p, cwd, sbases, w)
        else:
            self.shell(data.decode("utf-8", "replace"), cwd, sbases, w)

    # -- python ----------------------------------------------------------------------------------------
    def python_source(self, data, path, cwd, bases, where):
        ctx = self.ctx
        pseudo = path or ((cwd.rstrip("/") + "/" if cwd else "") + "__inline__.py")
        try:
            tree = ast.parse(data, filename=pseudo)
        except (SyntaxError, ValueError):
            self.reason("unparseable local script (fail-closed): " + pseudo + where)
            return
        names = fd.module_imports(data, pseudo, fd.STATIC_ROOTS)
        if names is not None and ctx.references_track_c(names):
            self.reason("python run by the workflow imports Track C modules: " + pseudo + where)
        doc_ids = set()
        for n in ast.walk(tree):
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for st in n.body:
                    if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):
                        doc_ids.add(id(st.value))
        for n in ast.walk(tree):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_ids:
                self.scan_text(n.value, bases, where)
                if "\n" not in n.value:
                    for words in self.commands(n.value):
                        if _is_launcher(words):
                            self.command(words, cwd, bases, where)
            elif isinstance(n, (ast.List, ast.Tuple)) and n.elts:
                words = []
                for e in n.elts:
                    if isinstance(e, ast.Constant) and isinstance(e.value, str):
                        words.append(e.value)
                    elif isinstance(e, ast.Attribute) and e.attr == "executable":
                        words.append("python")
                    else:
                        break
                if _is_launcher(words):
                    self.command(words, cwd, bases, where)

    # -- pytest selections -----------------------------------------------------------------------------
    def pytest(self, args, cwd, where):
        ctx = self.ctx
        exprs, positional = [], []
        args = list(args)
        while args:
            a = args.pop(0)
            if a == "--":
                positional += args
                break
            if a.startswith("--"):
                name, eq, value = a.partition("=")
                if name in PYTEST_VALUE_LONG and not eq and args:
                    args.pop(0)
                continue
            if a.startswith("-") and len(a) > 1:
                cluster = a[1:]
                for j, ch in enumerate(cluster):
                    if ch in PYTEST_VALUE_SHORT:
                        value = cluster[j + 1:] or (args.pop(0) if args else "")
                        if ch in "km":
                            exprs.append((ch, value))
                        break
                continue
            positional.append(a)
        targets, whole = [], not exprs
        for kind, expr in exprs:
            words = [x for x in re.findall(r"[A-Za-z0-9_.\[\]-]+", expr) if x not in ("and", "or", "not")]
            hit = [x for x in words if ctx.names_track_c_tests(kind, x)]
            if hit:
                targets.append(("-%s %s" % (kind, expr), None))
        for a in positional:
            path = a.split("::", 1)[0]
            cands = set()
            for c in resolve(path, [cwd]):
                if any(ch in c for ch in "*?["):
                    cands.update(q for q in ctx.files if fnmatch.fnmatchcase(q, c)
                                 and "/" not in q[len(c.rsplit("/", 1)[0]) + 1:])
                else:
                    cands.add(c)
            if not cands:
                whole = False
            for c in sorted(cands):
                if c in ctx.files:
                    whole = False
                    if c in ctx.tc_tests:
                        targets.append((a, {c}))
                elif any(q.startswith(c + "/") for q in ctx.files):
                    # a directory holding only Track C tests is a Track C selection; a directory that
                    # also holds other capabilities' tests is a suite run (note); none: not Track C
                    under = {q for q in ctx.tc_tests if q.startswith(c + "/")}
                    other = any(q.startswith(c + "/") and q not in ctx.tc_tests for q in ctx.test_files)
                    if under and not other:
                        targets.append((a, under))
                        whole = False
                    elif not under:
                        whole = False
                else:
                    whole = False
        if targets:
            labels = sorted({label for label, _ in targets})
            if all(paths is not None and paths <= ctx.av for _, paths in targets):
                self.av_ref = self.av_ref or labels[0]
                self.reason("references an A_V path: " + labels[0], "av", labels[0])
            else:
                text = "pytest " + " ".join(labels) + where
                self.reason("runs a Track C test selection: " + text, "tests", text)
        elif whole:
            self.note("runs the whole pytest suite (cwd %s)%s: not a spoof by itself" % (cwd or ".", where))

    # -- workflow structure ----------------------------------------------------------------------------
    def steps(self, steps_node, wd_default, where, inherited_bases=()):
        for st in seq(steps_node):
            wd = (scalars(st, "working-directory") or [wd_default or ""])[-1]
            bases = sorted({wd, ""} | set(inherited_bases))
            shell_name = (scalars(st, "shell") or [None])[-1]
            for run in scalars(st, "run"):
                self.shell(run, wd, bases, where, shell_name)
            for uses in scalars(st, "uses"):
                self.uses(uses, wd, where)
            for w in get_all(st, "with"):
                for v in all_scalars(w):
                    self.scan_text(v, bases, where)

    def uses(self, uses, wd, where):
        if not uses.startswith("./"):
            return
        target = _norm(uses[2:]) or ""
        if target == fd.TRACK_C_WORKFLOW:
            self.reason("calls the Track C workflow: " + uses + where)
            return
        if target in self.visited:
            return
        self.visited.add(target)
        ctx = self.ctx
        if is_workflow_path(target) and target in ctx.files:
            self.followed.append(target)
            try:
                root = load(ctx.read(target))
                ident = identity(root)
            except Unparseable as exc:
                self.reason("unparseable reusable workflow (fail-closed): %s (%s)" % (target, exc))
                return
            self.workflow_body(root, ident, " (via %s)" % target)
            return
        meta = [p for p in ((target + "/" if target else "") + "action.yml", (target + "/" if target else "") + "action.yaml")
                if p in ctx.files]
        if not meta:
            self.reason("local action metadata unresolvable (fail-closed): " + uses + where)
            return
        p = meta[0]
        self.followed.append(p)
        w = " (via %s)" % p
        try:
            root = load(ctx.read(p))
        except Unparseable as exc:
            self.reason("unparseable local action (fail-closed): %s (%s)" % (p, exc))
            return
        for v in all_scalars(root):
            self.scan_text(v, [wd, "", target], w)
        for runs in get_all(root, "runs"):
            using = (scalars(runs, "using") or [""])[-1]
            if using == "composite":
                for steps in get_all(runs, "steps"):
                    self.steps(steps, wd, w, inherited_bases=(target,))

    def workflow_body(self, root, ident, where=""):
        top_wd = default_wd(root)
        for v in all_scalars(root):
            self.scan_text(v, [top_wd or ""], where)
        for _, job in ident["jobs"]:
            job_wd = default_wd(job) or top_wd
            for u in scalars(job, "uses"):
                self.uses(u, job_wd or "", where)
            for steps in get_all(job, "steps"):
                self.steps(steps, job_wd, where)


class Context:
    """What the analysis needs to know about T and the Track C projection."""

    def __init__(self, files, read, ns, av, tcm, references_track_c, ns_paths):
        self.files = set(files)
        self.read = read
        self.ns = ns
        self.av = set(av)
        self.ns_paths = sorted(ns_paths)
        self._tcm = tcm
        self._refs = references_track_c
        self.test_files = {p for p in self.files if p.endswith(".py") and _is_test_name(p.rsplit("/", 1)[-1])}
        self.tc_tests = {p for p in self.test_files if ns(p) or p in self.av}
        self._names = None

    def references_track_c(self, names):
        return self._refs(names, self._tcm)

    def names_track_c_tests(self, kind, word):
        """-k: a Track C test module or test/class name contains ``word``; -m: a Track C test marker."""
        if self._names is None:
            mods, defs, marks = set(), set(), set()
            for p in self.tc_tests:
                mods.add(p.rsplit("/", 1)[-1][:-3].casefold())
                try:
                    tree = ast.parse(self.read(p))
                except (SyntaxError, ValueError):
                    continue
                for n in ast.walk(tree):
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        defs.add(n.name.casefold())
                    if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Attribute) and n.value.attr == "mark":
                        marks.add(n.attr.casefold())
            self._names = (mods, defs, marks)
        mods, defs, marks = self._names
        w = word.casefold()
        if kind == "m":
            return w in marks
        return any(w in m for m in mods) or any(w in d for d in defs)


def _launch_words(words):
    """Words of a simple command without leading NAME=VALUE assignments and wrapper commands."""
    words = list(words)
    while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in WRAPPERS):
        words.pop(0)
    return words


def _is_launcher(words):
    w = _launch_words(words)
    return bool(w) and (bool(PYTHON_RE.match(w[0])) or w[0] in ("pytest", "py.test", "source") + SHELLS)


def _is_test_name(base):
    return base.startswith("test_") and base.endswith(".py") or base.endswith("_test.py")


def analyse(ctx, path, data):
    """(identity or None, Analysis). Raises Unparseable / LoaderUnavailable."""
    root = load(data)
    ident = identity(root)
    a = Analysis(ctx, path)
    a.visited.add(path)
    a.workflow_body(root, ident)
    return ident, a


# =====================================================================================================
# Fix round 3 (CDR-014 §14): H1 identity keys with constant-expression folding, H2 mention-based
# over-approximation of what a complement workflow can run.
# =====================================================================================================
class NotConstant(Exception):
    """A GitHub expression that is not a foldable constant."""


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_-]*")
_INT_RE = re.compile(r"-?[0-9]+(?![0-9A-Za-z_.])")


class _ConstExpr:
    """Parser for the constant subset of GitHub expressions: string literals ('' escapes), true, false,
    null, decimal integers and format() over such arguments (nested)."""

    def __init__(self, text):
        self.t, self.i = text, 0

    def ws(self):
        while self.i < len(self.t) and self.t[self.i] in " \t\r\n":
            self.i += 1

    def parse(self):
        v = self.expr()
        self.ws()
        if self.i != len(self.t):
            raise NotConstant(self.t)
        return v

    def string(self):
        out = []
        self.i += 1
        while True:
            j = self.t.find("'", self.i)
            if j < 0:
                raise NotConstant("unterminated string")
            out.append(self.t[self.i:j])
            if self.t.startswith("''", j):
                out.append("'")
                self.i = j + 2
                continue
            self.i = j + 1
            return "".join(out)

    def expr(self):
        self.ws()
        if self.t.startswith("'", self.i):
            return self.string()
        m = _INT_RE.match(self.t, self.i)
        if m:
            self.i = m.end()
            return str(int(m.group(0)))
        m = _IDENT_RE.match(self.t, self.i)
        if not m:
            raise NotConstant(self.t[self.i:])
        name = m.group(0)
        self.i = m.end()
        self.ws()
        if self.t.startswith("(", self.i):
            if name.casefold() != "format":
                raise NotConstant(name)
            self.i += 1
            args = []
            self.ws()
            if not self.t.startswith(")", self.i):
                while True:
                    args.append(self.expr())
                    self.ws()
                    if self.t.startswith(",", self.i):
                        self.i += 1
                        continue
                    if self.t.startswith(")", self.i):
                        break
                    raise NotConstant("format arguments")
            self.i += 1
            return _format(args)
        if name == "true":
            return "true"
        if name == "false":
            return "false"
        if name == "null":
            return ""
        raise NotConstant(name)


def _format(args):
    if not args:
        raise NotConstant("format()")
    fmt, rest, out, i = args[0], args[1:], [], 0
    while i < len(fmt):
        c = fmt[i]
        if fmt.startswith("{{", i):
            out.append("{")
            i += 2
        elif fmt.startswith("}}", i):
            out.append("}")
            i += 2
        elif c == "{":
            j = fmt.find("}", i)
            idx = fmt[i + 1:j] if j > i else ""
            if not idx.isdigit() or int(idx) >= len(rest):
                raise NotConstant("format placeholder")
            out.append(rest[int(idx)])
            i = j + 1
        elif c == "}":
            raise NotConstant("format brace")
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _expr_end(text, k):
    """Index of the closing ``}}`` of an expression starting at ``k`` (string literals skipped), or -1."""
    i = k
    while i < len(text):
        if text[i] == "'":
            j = i + 1
            while True:
                j = text.find("'", j)
                if j < 0:
                    return -1
                if text.startswith("''", j):
                    j += 2
                    continue
                break
            i = j + 1
            continue
        if text.startswith("}}", i):
            return i
        i += 1
    return -1


def fold_expressions(text):
    """(text with every constant ``${{ ... }}`` replaced by its value, [non-foldable expressions])."""
    if not isinstance(text, str) or "${{" not in text:
        return text, []
    out, bad, i = [], [], 0
    while True:
        j = text.find("${{", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        end = _expr_end(text, j + 3)
        if end < 0:
            bad.append(text[j:])
            out.append(text[j:])
            break
        try:
            out.append(_ConstExpr(text[j + 3:end]).parse())
        except NotConstant:
            bad.append(text[j:end + 2])
            out.append(text[j:end + 2])
        i = end + 2
    return "".join(out), bad


_NON_KEY = re.compile(r"[^a-z0-9]")


def identity_keys(s):
    """H1: casefolded [a-z0-9] keys of s, NFKC(s), skeleton(s), skeleton(NFKC(s)), NFKC(skeleton(s))."""
    s = s or ""
    nf = lambda x: unicodedata.normalize("NFKC", x)  # noqa: E731
    forms = {s, nf(s), skeleton(s), skeleton(nf(s)), nf(skeleton(s))}
    return {_NON_KEY.sub("", f.casefold()) for f in forms}


def identity_claim(value, track_c_values):
    """The (Track C key, workflow key) pair if a Track C key is a substring of a key of ``value``."""
    keys = identity_keys(value)
    for tv in track_c_values:
        for tk in sorted(identity_keys(tv)):
            if not tk:
                continue
            for k in sorted(keys):
                if tk in k:
                    return tk, k
    return None


# ---- the Track C mention set M --------------------------------------------------------------------------
_CANON_NON_ID = re.compile(r"[^a-z0-9._/-]+")
_CANON_JOIN = re.compile(r"[._/-]+")
_CANON_MIXED = re.compile(r"[\x00\x01]*\x00[\x00\x01]*")


def canonical_text(text):
    """Casefolded text with every run of non-identifier characters as \\x00 (token boundary) and every
    run of the joiners . _ - / as \\x01 (part boundary inside a token)."""
    t = _CANON_NON_ID.sub("\x00", text.casefold())
    t = _CANON_JOIN.sub("\x01", t)
    return _CANON_MIXED.sub("\x00", t)


class Mentions:
    """The Track C mention set M (authenticated names only) and a matcher over canonical text."""

    KIND_ORDER = ("av", "tool", "test", "module", "workflow")

    def __init__(self, elements):
        """``elements``: {display string: kind}; kinds: av, tool, test, module, workflow."""
        self.items = {}
        self.skipped = []
        for disp, kind in sorted(elements.items(), key=lambda kv: (self.KIND_ORDER.index(kv[1]), kv[0])):
            c = canonical_text(disp).strip("\x01")
            if not c or "\x00" in c:
                self.skipped.append(disp)
                continue
            prev = self.items.get(c)
            if prev is None or self.KIND_ORDER.index(kind) < self.KIND_ORDER.index(prev[1]):
                self.items[c] = (disp, kind)
        alts = sorted(self.items, key=lambda c: (-len(c), c))
        self.rx = re.compile("(?<![a-z0-9])(%s)(?![a-z0-9])" % "|".join(re.escape(a) for a in alts)) if alts else None

    def find(self, text):
        """[(display, kind)] of every element of M mentioned in ``text`` (sorted, unique)."""
        if self.rx is None or not text:
            return []
        c = canonical_text(text)
        hits = {self.items[m.group(1)] for m in self.rx.finditer(c)}
        return sorted(hits, key=lambda x: (self.KIND_ORDER.index(x[1]), x[0]))

    def record(self):
        out = {}
        for disp, kind in self.items.values():
            out.setdefault(kind, []).append(disp)
        return {k: sorted(v) for k, v in sorted(out.items())}


def build_mentions(tool_paths, test_paths, modules, av, track_c_workflow):
    """M from authenticated references: tool stems/basenames, Track C test module stems, Track C module
    dotted paths, A_V basenames (and stems of A_V Python files), the Track C workflow path/basename."""
    el = {}

    def add(disp, kind):
        if disp and disp not in el:
            el[disp] = kind

    for p in sorted(av):
        base = p.rsplit("/", 1)[-1]
        add(base, "av")
        if base.endswith(".py"):
            add(base[:-3], "av")
    for p in sorted(tool_paths):
        base = p.rsplit("/", 1)[-1]
        add(base, "tool")
        add(base[:-3] if base.endswith(".py") else base, "tool")
    for p in sorted(test_paths):
        base = p.rsplit("/", 1)[-1]
        add(base[:-3] if base.endswith(".py") else base, "test")
    for m in sorted(modules):
        add(m, "module")
    add(track_c_workflow, "workflow")
    add(track_c_workflow.rsplit("/", 1)[-1], "workflow")
    return Mentions(el)


# ---- text variants -------------------------------------------------------------------------------------
_ANSI_C = re.compile(r"\$'((?:[^'\\]|\\.)*)'", re.S)
_ANSI_ESC = re.compile(r"\\(x[0-9A-Fa-f]{1,2}|u[0-9A-Fa-f]{1,4}|U[0-9A-Fa-f]{1,8}|[0-7]{1,3}|.)", re.S)
_ANSI_SIMPLE = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f",
                "v": "\v", "\\": "\\", "'": "'", '"': '"', "?": "?"}


def _ansi_unescape(body):
    def one(m):
        e = m.group(1)
        try:
            if e[0] in "xuU" and len(e) > 1:
                return chr(int(e[1:], 16))
            if e[0] in "01234567":
                return chr(int(e, 8))
        except (ValueError, OverflowError):
            return m.group(0)
        return _ANSI_SIMPLE.get(e, m.group(0))
    return _ANSI_ESC.sub(one, body)


def text_variants(text, path=None, data=None):
    """The texts a file is scanned as: as is; backslash-newline and quotes removed; ANSI-C $'...'
    decoded; for Python files also the decoded string constants."""
    out = [text]
    flat = text.replace("\\\r\n", "").replace("\\\n", "")
    out.append(flat.replace("'", "").replace('"', "").replace("`", ""))
    if "$'" in text:
        out.append(_ANSI_C.sub(lambda m: _ansi_unescape(m.group(1)), text))
    if path and path.endswith(".py") and data is not None:
        try:
            tree = ast.parse(data)
        except (SyntaxError, ValueError):
            tree = None
        if tree is not None:
            consts = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)):
                    consts.append(n.value if isinstance(n.value, str) else n.value.decode("utf-8", "replace"))
            if consts:
                out.append("\n".join(consts))
    return out


# ---- imports, pytest selections, module launches (text level) -----------------------------------------
_FROM_RX = re.compile(r"(?<![\w.])from\s+([A-Za-z_][\w.]*)\s+import\s+\(?\s*([A-Za-z_*][\w\s,.*]*)")
_IMPORT_RX = re.compile(r"(?<![\w.])import\s+([A-Za-z_][\w.]*(?:\s+as\s+\w+)?(?:\s*,\s*[A-Za-z_][\w.]*(?:\s+as\s+\w+)?)*)")
_DYN_RX = re.compile(r"(?:import_module|__import__|run_module)\(\s*['\"]([A-Za-z_][\w.]*)['\"]")
_PYTEST_SEL = re.compile(r"(?<![\w-])-[A-Za-z]*?([km])(?:\s*=\s*|[\s,]+|(?=[A-Za-z0-9_'\"(]))"
                         r"(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))")
_SEL_WORD = re.compile(r"[A-Za-z0-9_]+(?:[.\[\]-][A-Za-z0-9_]+)*")
_PYTEST_EXCLUDE = re.compile(r"--(ignore-glob|ignore|deselect)(?:\s*=\s*|\s+)(?:'([^']*)'|\"([^\"]*)\"|([^\s'\"]+))")
_MODULE_RUN = re.compile(r"(?:(?<![\w-])-m\s*|run_module\(\s*['\"])([A-Za-z_][\w.]*)")


def text_imports(text):
    names = set()
    for m in _FROM_RX.finditer(text):
        mod = m.group(1).strip(".")
        if not mod:
            continue
        names.add(mod)
        for part in m.group(2).replace("(", " ").replace(")", " ").split(","):
            w = part.strip().split()
            if w and w[0] != "*" and w[0].isidentifier():
                names.add(mod + "." + w[0])
    for m in _IMPORT_RX.finditer(text):
        for part in m.group(1).split(","):
            w = part.strip().split()
            if w:
                names.add(w[0].strip("."))
    names.update(m.group(1) for m in _DYN_RX.finditer(text))
    return {n for n in names if n}


def pytest_selections(text):
    """[(kind, expression)] for every -k/-m option-like occurrence in ``text``."""
    out = []
    for m in _PYTEST_SEL.finditer(text):
        expr = next((g for g in m.groups()[1:] if g is not None), "")
        out.append((m.group(1), expr))
    return out


# ---- reach tokens ---------------------------------------------------------------------------------------
_REACH_TOKEN = re.compile(r"[^\s'\"`;&|<>(){}$,=:@!#]+")
_ARGSFILE = re.compile(r"(?<![\w@])@([^\s'\"`;&|<>(){}$,=:@!#]+)")
_GLOB_CHARS = "*?["
MAKE_WORDS = ("make", "gmake")
MAKE_FILES = ("Makefile", "makefile", "GNUmakefile")
PACKAGE_WORDS = ("npm", "yarn", "pnpm", "tox", "nox")
PACKAGE_FILES = ("package.json", "pyproject.toml", "tox.ini", "noxfile.py")
# Files whose content can decide what runs (scripts, workflow/action YAML, build and test configuration,
# extension-less or shebang executables). A reached file of another kind (data, documents) is not code: it
# is neither scanned nor followed (a tool named only inside data read at run time is a dynamically
# constructed invocation, D3-c). Files under a local action directory and pytest @argsfiles are always
# scanned.
CODE_SUFFIXES = (".sh", ".bash", ".zsh", ".ksh", ".dash", ".py", ".pyw", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts",
                 ".rb", ".pl", ".ps1", ".psm1", ".bat", ".cmd", ".yml", ".yaml", ".mk", ".ini", ".cfg", ".toml",
                 ".args", ".r", ".lua", ".php", ".groovy", ".gradle", ".nix", ".dockerfile")
CODE_NAMES = MAKE_FILES + PACKAGE_FILES + ("Dockerfile", "Containerfile", "setup.py", "setup.cfg", "pytest.ini",
                                           ".pytest.ini", "conftest.py", "sitecustomize.py", "usercustomize.py")


def is_code(path, head=b""):
    base = path.rsplit("/", 1)[-1]
    if base in CODE_NAMES or base.casefold().endswith(CODE_SUFFIXES) or head.startswith(b"#!"):
        return True
    return "." not in base.lstrip(".")


_REMOTE_USES = re.compile(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(/[^@]*)?@(.+)$")
_GITHUB_REPO = re.compile(r"github\.com[/:]([^/\s]+)/([^/\s]+?)(?:\.git)?/?$")


def repo_identity(url):
    """(owner, repo) casefolded of a GitHub remote URL, or None."""
    m = _GITHUB_REPO.search(url or "")
    return (m.group(1).casefold(), m.group(2).casefold()) if m else None


def reach_tokens(text):
    out = set()
    for tok in _REACH_TOKEN.findall(text):
        for t in {tok, tok.replace("\\", "/")} if "\\" in tok else {tok}:
            t = t.strip(".,")
            if "]" in t and "[" not in t:          # a closing bracket of a list literal, not a glob class
                t = t.replace("]", "")
            out.add(t)
            if t.startswith("-") and not t.startswith("--") and len(t) > 2:
                out.add(t[2:])             # attached short-option value (-cfile.ini)
    return out


def components(token):
    comps = []
    for c in token.split("/"):
        if c in ("", "."):
            continue
        if c == "..":
            if comps:
                comps.pop()
            continue
        comps.append(c)
    return comps


class ScanContext:
    """What the H2 scan needs to know about T, the Track C projection and the verifier."""

    def __init__(self, files, read, blob, ns, av, mentions, tcm, references_track_c, tc_tests, test_files,
                 ns_paths, track_c_workflow, repo_ids, verifier_self, names_track_c_tests):
        self.files = set(files)
        self.read, self.blob, self.ns, self.av = read, blob, ns, set(av)
        self.mentions, self.tcm, self._refs = mentions, set(tcm), references_track_c
        self.tc_tests, self.test_files = set(tc_tests), set(test_files)
        self.ns_paths = sorted(ns_paths)
        self.track_c_workflow = track_c_workflow
        self.repo_ids = set(repo_ids)
        self.verifier_self = verifier_self
        self.names_track_c_tests = names_track_c_tests
        self.sorted_files = sorted(self.files)
        self._globs = {}
        self.by_base = {}
        for p in self.files:
            self.by_base.setdefault(p.rsplit("/", 1)[-1], []).append(p)
        self.dirs = fd.all_dirs(self.files)
        self.dirs_by_base = {}
        for d in self.dirs:
            self.dirs_by_base.setdefault(d.rsplit("/", 1)[-1], []).append(d)

    def references_track_c(self, names):
        return self._refs(names, self.tcm)

    def glob_rx(self, pattern):
        """A compiled matcher for ``pattern`` and ``*/pattern`` (path-suffix semantics, any cwd)."""
        if pattern not in self._globs:
            self._globs[pattern] = re.compile("(?:%s)|(?:%s)" % (fnmatch.translate(pattern),
                                                                 fnmatch.translate("*/" + pattern)))
        return self._globs[pattern]

    def named_files(self, comps):
        """Tree files a token names: exact path, path suffix (any cwd) or, for one component, basename;
        a token longer than the path (absolute runner paths) names the files it ends with."""
        out = set()
        for f in self.by_base.get(comps[-1], ()):
            fc = f.split("/")
            n = min(len(fc), len(comps))
            if fc[-n:] == comps[-n:]:
                out.add(f)
        return out

    def named_dirs(self, comps):
        out = set()
        for d in self.dirs_by_base.get(comps[-1], ()):
            dc = d.split("/")
            n = min(len(dc), len(comps))
            if dc[-n:] == comps[-n:]:
                out.add(d)
        return out


class Scan:
    """H2 over-approximation for one complement workflow: every reason is a mention of Track C scope in
    the workflow or in an in-tree file it can reach (see the module docstring)."""

    def __init__(self, ctx, path):
        self.ctx, self.path = ctx, path
        self.reasons, self.references = [], set()
        self._categories = set()
        self.av_ref = None
        self.reached, self.self_placement, self.out_of_tree, self.notes = [], [], [], []
        self.visited = set()
        self.queue, self.queued = collections.deque(), set()

    def reason(self, text, category=None, ref=None):
        if ref is not None:
            self.references.add("%s: %s" % (category or "reason", ref))
        if category is not None:
            if category in self._categories:
                return
            self._categories.add(category)
        if text not in self.reasons:
            self.reasons.append(text)

    @staticmethod
    def _where(p, root):
        return "" if p == root else " (via %s)" % p

    # -- entry --------------------------------------------------------------------------------------
    def run(self, data, root_node):
        self.visited.add(self.path)
        self.scan_file(self.path, data, False, root_node=root_node, yaml_kind="workflow")
        while self.queue:
            p, ctx_pytest, kind = self.queue.popleft()
            self.queued.discard(p)
            if p in self.visited:
                continue
            self.visited.add(p)
            self.reached.append(p)
            data = self.ctx.read(p)
            self.scan_file(p, data, ctx_pytest, yaml_kind=kind)
        return self

    def enqueue(self, p, pytest_ctx, kind=None, via=None, specific=True, force=False):
        """Queue a reached tree file (Track C, A_V, the Track C workflow and the verifier's own files are
        never scanned as content: naming them is the finding, or they are the auditor itself)."""
        ctx = self.ctx
        where = self._where(via, self.path) if via else ""
        if p == ctx.track_c_workflow:
            self.reason("names the Track C workflow: %s%s" % (p, where), "workflow", p + where)
            return
        if p in ctx.av:
            if specific:
                self.av_ref = self.av_ref or p
                self.reason("references an A_V path: %s%s" % (p, where), "av", p + where)
            return
        if ctx.ns(p):
            if specific:
                self.reason("names a Track C file: %s%s" % (p, where), "ns-file", p + where)
            return
        if p in self.visited or p in self.queued:
            return
        if not (force or kind or is_code(p, ctx.read(p)[:2])):
            return
        if ctx.verifier_self is not None and ctx.verifier_self.is_self(p, ctx.blob(p), ctx.read, ctx.files, ctx.blob):
            if p not in [x["path"] for x in self.self_placement]:
                self.self_placement.append({"path": p, "blob": ctx.blob(p)})
            return
        self.queue.append((p, pytest_ctx, kind))
        self.queued.add(p)

    # -- one file -----------------------------------------------------------------------------------
    def scan_file(self, p, data, pytest_ctx, root_node=None, yaml_kind=None):
        ctx = self.ctx
        where = self._where(p, self.path)
        text = data.decode("utf-8", "replace")
        variants = text_variants(text, p, data)
        is_yaml = p.casefold().endswith((".yml", ".yaml"))
        if is_yaml and root_node is None and yaml is not None:
            try:
                root_node = load(data)
            except Unparseable as exc:
                if yaml_kind in ("reusable", "action"):
                    self.reason("unparseable %s (fail-closed): %s (%s)" % (
                        "reusable workflow" if yaml_kind == "reusable" else "local action", p, exc))
                root_node = None
        if root_node is not None:
            decoded = [fold_expressions(v)[0] for v in all_scalars(root_node)]
            variants.append("\n".join(decoded))
            self.uses_of(root_node, p, where)
        pytest_ctx = pytest_ctx or any("pytest" in v.casefold() or "py.test" in v.casefold() for v in variants)
        if p.endswith(".py"):
            names = fd.module_imports(data, p, fd.STATIC_ROOTS)
            if names is None:
                self.reason("unparseable local script (fail-closed): %s" % p, None, p)
            elif ctx.references_track_c(names):
                self.reason("imports Track C modules: %s%s" % (p, where), "import", p)
        words = set()
        for v in variants:
            for disp, kind in ctx.mentions.find(v):
                if kind == "av":
                    self.av_ref = self.av_ref or disp
                    self.reason("references an A_V path: %s%s" % (disp, where), "av", disp + where)
                else:
                    self.reason("mentions Track C scope: %s %s%s" % (kind, disp, where), "mention-" + kind,
                                disp + where)
            imp = text_imports(v)
            if imp and ctx.references_track_c(imp):
                hit = sorted(n for n in imp if ctx.references_track_c([n]))[0]
                self.reason("imports Track C modules: %s%s" % (hit, where), "import", hit + where)
            if pytest_ctx:
                for kind, expr in pytest_selections(v):
                    sel = [w for w in _SEL_WORD.findall(expr) if w not in ("and", "or", "not")]
                    hit = [w for w in sel if ctx.names_track_c_tests(kind, w)]
                    if hit:
                        self.reason("selects Track C tests: -%s %s%s" % (kind, expr, where), "pytest-select",
                                    "-%s %s%s" % (kind, expr, where))
            if pytest_ctx:
                self.pytest_exclusions(v, where)
            for mod in _MODULE_RUN.findall(v):
                self.module_run(mod, pytest_ctx, p, where)
            for tok in reach_tokens(v):
                self.token(tok, pytest_ctx, p, where)
            for tok in _ARGSFILE.findall(v):
                comps = components(tok.replace("\\", "/"))
                for f in sorted(ctx.named_files(comps)) if comps else ():
                    self.enqueue(f, True, via=p, specific=len(comps) > 1, force=True)
            words.update(w for w in re.split(r"[^a-z0-9]+", v.casefold()) if w)
        if words & set(MAKE_WORDS):
            for f in ctx.sorted_files:
                b = f.rsplit("/", 1)[-1]
                if b in MAKE_FILES or b.endswith(".mk"):
                    self.enqueue(f, pytest_ctx, via=p, specific=False)
        if words & set(PACKAGE_WORDS):
            for f in ctx.sorted_files:
                if f.rsplit("/", 1)[-1] in PACKAGE_FILES:
                    self.enqueue(f, pytest_ctx, via=p, specific=False)

    def pytest_exclusions(self, text, where):
        """pytest --ignore/--ignore-glob/--deselect values in ``text`` (cwd-independent: path-suffix
        semantics). FOUND when they remove other capabilities' tests and keep Track C tests: a narrowed
        selection that runs Track C tests (pytest over the unnarrowed whole suite stays a note)."""
        ctx = self.ctx
        pats = []
        for m in _PYTEST_EXCLUDE.finditer(text):
            value = next((g for g in m.groups()[1:] if g is not None), "")
            comps = components(value.split("::", 1)[0].replace("\\", "/"))
            if comps:
                pats.append((m.group(1), "/".join(comps)))
        if not pats:
            return

        def excluded(q):
            for kind, pat in pats:
                if kind == "ignore-glob":
                    if ctx.glob_rx(pat).match(q):
                        return True
                elif q == pat or q.endswith("/" + pat) or q.startswith(pat + "/") or ("/" + pat + "/") in ("/" + q):
                    return True
            return False

        tests = sorted(ctx.test_files | ctx.tc_tests)
        narrowed = [q for q in tests if q not in ctx.tc_tests and excluded(q)]
        kept = [q for q in tests if q in ctx.tc_tests and not excluded(q)]
        if narrowed and kept:
            label = " ".join("--%s %s" % kp for kp in pats)
            self.reason("pytest exclusions narrow the suite and keep Track C tests: %s%s" % (label, where),
                        "pytest-exclude", label + where)

    def whole_directories(self, rx, hits):
        """True when every Track C path the glob matches lies in a directory that also holds other
        capabilities' tests and the glob matches every test there (a whole-suite glob such as test_*.py)."""
        ctx = self.ctx
        for d in {q.rsplit("/", 1)[0] if "/" in q else "" for q in hits}:
            tests_d = [t for t in ctx.test_files | ctx.tc_tests if (t.rsplit("/", 1)[0] if "/" in t else "") == d]
            if not any(t not in ctx.tc_tests for t in tests_d) or not all(rx.match(t) for t in tests_d):
                return False
        return True

    def whole_kind(self, rx, pattern):
        """True when the glob matches every tree file with its literal suffix (``*.py``, ``**/*.py``): it
        selects a whole kind of file, not Track C files."""
        last = pattern.rsplit("/", 1)[-1]
        if "." not in last:
            return False
        suffix = "." + last.rsplit(".", 1)[-1]
        if any(ch in suffix for ch in _GLOB_CHARS):
            return False
        same = [f for f in self.ctx.sorted_files if f.endswith(suffix)]
        return bool(same) and all(rx.match(f) for f in same)

    def note(self, text):
        if text not in self.notes:
            self.notes.append(text)

    def module_run(self, mod, pytest_ctx, p, where):
        parts = mod.strip(".").split(".")
        if not parts or not all(x.isidentifier() for x in parts):
            return
        for comps in (parts[:-1] + [parts[-1] + ".py"], parts + ["__main__.py"], parts + ["__init__.py"]):
            for f in sorted(self.ctx.named_files(comps)):
                fc = f.split("/")
                if len(fc) < len(comps) or fc[-len(comps):] != comps:
                    continue
                specific = len(parts) > 1
                if specific and (self.ctx.ns(f) or f in self.ctx.av) and f != self.ctx.track_c_workflow:
                    self.reason("runs a Track C module: -m %s%s" % (mod, where), "module-run", mod + where)
                self.enqueue(f, pytest_ctx, via=p, specific=specific)

    def token(self, tok, pytest_ctx, p, where):
        ctx = self.ctx
        tok = tok.lstrip("!")
        comps = components(tok)
        if not comps:
            return
        joined = "/".join(comps)
        if any(ch in joined for ch in _GLOB_CHARS):
            rx = ctx.glob_rx(joined)
            if "/" in joined or joined.endswith(".py"):
                hits = [q for q in ctx.ns_paths if rx.match(q)]
                if hits and (self.whole_directories(rx, hits) or self.whole_kind(rx, joined)):
                    self.note("glob over every test of its directories or every file of its kind (whole-suite "
                              "selection, not a spoof by itself): %s%s" % (tok, where))
                elif hits:
                    self.reason("glob matches Track C paths: %s%s" % (tok, where), "glob", tok + where)
            if "/" in joined:
                for f in ctx.sorted_files:
                    if rx.match(f):
                        self.enqueue(f, pytest_ctx, via=p, specific=False)
            return
        if len(comps) > 1:
            for i in range(len(comps) - 1):
                suffix = "/".join(comps[i:])
                for c in (suffix, fd.IMPL + "/" + suffix):
                    if c not in ctx.files and c not in ctx.dirs and ctx.ns(c):
                        self.reason("names a Track C namespace path: %s%s" % (tok, where), "ns-path", tok + where)
        for f in sorted(ctx.named_files(comps)):
            self.enqueue(f, pytest_ctx, via=p, specific=len(comps) > 1)
        for d in sorted(ctx.named_dirs(comps)):
            under = {q for q in ctx.tc_tests if q.startswith(d + "/")}
            other = any(q.startswith(d + "/") and q not in ctx.tc_tests for q in ctx.test_files)
            if under and not other:
                self.reason("names a directory holding only Track C tests: %s%s" % (d, where), "tc-dir", d + where)

    # -- uses: local actions / reusable workflows / remote code -------------------------------------
    def uses_of(self, root_node, p, where):
        for u in uses_values(root_node):
            u, _ = fold_expressions(u.strip())
            self.uses(u, p, where)

    def uses(self, u, p, where):
        ctx = self.ctx
        if u.startswith("./") or u == ".":
            target = "/".join(components(u))
            if target == ctx.track_c_workflow:
                self.reason("calls the Track C workflow: %s%s" % (u, where), "workflow", u + where)
                return
            if is_workflow_path(target) and target in ctx.files:
                self.enqueue(target, False, kind="reusable", via=p)
                return
            meta = [m for m in ((target + "/" if target else "") + "action.yml", (target + "/" if target else "") + "action.yaml")
                    if m in ctx.files]
            if not meta:
                self.reason("local action metadata unresolvable (fail-closed): %s%s" % (u, where))
                return
            prefix = target + "/" if target else ""
            self.enqueue(meta[0], False, kind="action", via=p, specific=False)
            for f in ctx.sorted_files:
                if f.startswith(prefix) and f != meta[0]:
                    self.enqueue(f, False, via=p, specific=False, force=True)
            return
        if u.startswith("docker://"):
            self.out_of_tree.append({"in": p, "uses": u})
            return
        m = _REMOTE_USES.match(u)
        if m and (m.group(1).casefold(), m.group(2).casefold()) in ctx.repo_ids:
            self.reason("same-repository remote workflow or action, content not in T (fail-closed): %s%s" % (u, where),
                        None, u + where)
            return
        self.out_of_tree.append({"in": p, "uses": u})


def uses_values(node, seen=None):
    """Every scalar value of a ``uses`` key anywhere in a YAML node tree (jobs, steps, composite steps)."""
    seen = set() if seen is None else seen
    if node is None or yaml is None or id(node) in seen:
        return []
    seen.add(id(node))
    out = []
    if isinstance(node, yaml.MappingNode):
        for k, v in _items(node):
            if k == "uses" and isinstance(v, yaml.ScalarNode):
                out.append(v.value)
            else:
                out += uses_values(v, seen)
    elif isinstance(node, yaml.SequenceNode):
        for v in node.value:
            out += uses_values(v, seen)
    return out


class VerifierSelf:
    """The running FPIA verifier's own files (self-placement, AC-41): files under the verifier's directory
    or Python files importing it, byte-identical (same path) to the running verifier's file or to a version
    of that path on the verifier checkout's own history. Authenticating the verifier is D3-a."""

    def __init__(self, here, git_env=None):
        import subprocess
        self._subprocess = subprocess
        self.here = here
        self.root = here.parents[2] if len(here.parents) > 2 else here
        try:
            self.dir_rel = here.relative_to(self.root).as_posix()
        except ValueError:
            self.dir_rel = None
        self.package = fd.dir_dotted(self.dir_rel, fd.IMPL) if self.dir_rel else None
        self.git_env = git_env
        self._hist = {}

    def record(self):
        return {"verifier_dir": self.dir_rel, "verifier_package": self.package,
                "rule": "byte-identical (path and blob) to the running verifier's file or to a version of that "
                        "path on the verifier checkout's history; verifier directory or Python files importing "
                        "the verifier package (authentication of the verifier: open decision D3-a)"}

    def _blobs(self, p):
        if p in self._hist:
            return self._hist[p]
        out = set()
        f = self.root / p
        if f.is_file():
            try:
                out.add(_blob_id(f.read_bytes()))
            except OSError:
                pass
        try:
            proc = self._subprocess.run(["git", "--literal-pathspecs", "-C", str(self.root), "log", "--format=",
                                         "--raw", "--no-abbrev", "--no-renames", "HEAD", "--", p],
                                        capture_output=True, env=self.git_env)
            if proc.returncode == 0:
                for line in proc.stdout.decode("utf-8", "replace").split("\n"):
                    if line.startswith(":"):
                        meta = line.split("\t", 1)[0].split()
                        out.update(x for x in meta[2:4] if x.strip("0"))
        except OSError:
            pass
        self._hist[p] = out
        return out

    def is_self(self, p, blob, read, files, blob_of, _seen=None):
        """True for a file of the verifier itself: under the verifier directory, or a Python file that
        imports the verifier package directly or through another such file (FPIA's tests import it through
        their testkit) - and byte-identical to a version of that path on the verifier's history."""
        if self.dir_rel is None or blob is None or blob not in self._blobs(p):
            return False
        if p.startswith(self.dir_rel + "/"):
            return True
        if not p.endswith(".py") or not self.package:
            return False
        seen = set() if _seen is None else _seen
        if p in seen:
            return False
        seen.add(p)
        names = fd.module_imports(read(p), p, fd.STATIC_ROOTS) or ()
        if any(n == self.package or n.startswith(self.package + ".") for n in names):
            return True
        for n in sorted(names):
            for root in fd.STATIC_ROOTS:
                base = root + "/" + n.replace(".", "/")
                for q in (base + ".py", base + "/__init__.py"):
                    if q in files and q != p and self.is_self(q, blob_of(q), read, files, blob_of, seen):
                        return True
        return False


def _blob_id(data):
    import hashlib
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
