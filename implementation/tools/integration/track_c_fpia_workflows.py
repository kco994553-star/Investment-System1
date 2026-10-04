"""FPIA complement-workflow analysis for AC-32.spoof (fix round 2: G1, G2).

G1 - workflow identity. Workflow files are read with a real YAML loader (PyYAML ``safe_load`` as the
validity gate, ``compose`` with the pure-Python SafeLoader for the decoded scalar text, so quoting,
escapes, comments, tags, block scalars, anchors and duplicate keys are resolved as YAML resolves them).
A file that is not valid YAML for GitHub (not loadable, top level not a mapping, no jobs mapping) is
"unparseable workflow (fail-closed)". Names are compared after normalisation:
NFKC, casefold, removal of Default_Ignorable_Code_Point characters (zero-width and format characters),
and the UTS #39 confusable skeleton (NFD, prototype mapping, NFD). Two orders are compared and either
equality counts: N1 = skeleton(strip(NFKC(casefold(NFKC(s))))) and N2 = NFKC(casefold(skeleton(strip(NFKC(s))))),
so case variants (N1) and case-dependent confusables such as capital I for l (N2) are both caught.

Confusable source (no download at run time): the prototype table below was extracted once from the
system ICU (libicu74 74.2-1ubuntu3.1, ICU 74.2, Unicode 15.1.0 security data = UTS #39
confusables.txt) with ``uspoof_getSkeleton`` for every NFD-stable code point, keeping the mappings
whose source is NFKC-stable and whose prototype is ASCII (654 code points in 142 prototype groups),
because every compared name is NFKC-normalised first and the Track C name/stem is ASCII; a name whose
skeleton is not ASCII can only equal an ASCII skeleton through these entries. The Default_Ignorable
ranges come from the same ICU (``u_hasBinaryProperty`` UCHAR_DEFAULT_IGNORABLE_CODE_POINT, 4174 code
points). Format: ``<prototype hex code points joined by '.'>=<source code points, comma separated>``.

G2 - what a complement workflow runs. After YAML decoding, every scalar of the workflow is scanned for
path references; run steps are tokenised with shlex (quoting, ``cd``, env assignments, wrappers),
working-directory is joined to relative paths, local scripts invoked from run steps (sh/bash/python
files in the tree) and local composite actions / reusable workflows (``uses: ./path``) are followed
recursively with a cycle guard and scanned the same way, and pytest invocations are classified:
a selection that targets Track C tests (``-k``/``-m`` naming Track C test modules, test names or
markers, node ids or paths of Track C tests, directories holding only Track C tests) is a Track C test
invocation; pytest with no selection, or over a directory that also holds other capabilities' tests,
is a suite run and only a note.

Non-claim (open user decision D3-c): dynamically constructed invocations (string-built paths, paths in
shell variables, importlib with computed names) are not claimed to be detected
(``dynamic_invocation_detection: NOT_CLAIMED``). Job id/name collisions stay notes (open decision D3-b).
"""
from __future__ import annotations

import ast
import fnmatch
import posixpath
import re
import shlex
import unicodedata

try:
    import yaml
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
CONFUSABLE_SOURCE = {
    "table": "UTS #39 confusables (prototype skeleton), ASCII prototypes of NFKC-stable code points",
    "extracted_from": "ICU 74.2 (libicu74 74.2-1ubuntu3.1) uspoof_getSkeleton; Unicode 15.1.0 security data",
    "default_ignorable": "ICU 74.2 u_hasBinaryProperty(UCHAR_DEFAULT_IGNORABLE_CODE_POINT)",
    "runtime_download": False,
}

CONFUSABLES_ASCII = (
    "20=1680,2028,2029;21=1C3,2D51;26=A778;27=60,2B9,2BB,2BC,2BD,2BE,2C8,2CA,2CB,2F4,55A,55D,5D9,5F3,7F4,"
    "7F5,144A,16CC,2018,2019,201B,2032,2035,A78C,16F51,16F52;27.27=22,2BA,2EE,2F6,5F2,5F4,1CD3,201C,201D,"
    "201F,3003;27.42=181;27.44=18A;27.50=1A4;27.54=1AC;27.59=1B3;28=2768,2772,3014,FD3E;28.28=2E28;29=276"
    "9,2773,3015,FD3F;29.29=2E29;2A=66D,204E,2217,1031F;2B=16ED,2795,1029B;2C=60D,66B,201A,A4F9;2D=2D7,6D"
    "4,2010,2012,2013,2043,2212,2796,2CBA;2D.2E=A4FE;2E=660,6F0,701,702,A4F8,A60E,10A50,1D16D;2E.2C=A4FB;"
    "2E.2E=A4FA;2F=1735,2041,2044,2215,2571,27CB,29F8,2CC6,3033,30CE,31D3,4E3F,1D23A;2F.2F=2AFD;2F.2F.2F="
    "2AFB;32=1A7,3E8,14BF,A644,A6EF,A75A;33=1B7,21C,417,4E0,2CCC,A76A,A7AB,118CA,16F3B,1D206;34=13CE,118A"
    "F;35=1BC,118BB;36=431,13EE,2CD2,118D5;37=104D2,118C6,1D212;38=222,223,9EA,A6A,B03,1031A,1E8CB;39=9ED"
    ",A67,B68,D6D,2CCA,A76E,118AC,118CC,118D6;3A=2D0,2F8,589,5C3,703,704,903,A83,16EC,1803,1809,205A,2236"
    ",A4FD,A789;3C=2C2,1438,16B2,2039,276E,1D236;3C.3C=226A;3C.3C.3C=22D8;3D=1400,2E40,30A0,A4FF;3E=2C3,1"
    "433,203A,276F,16F3F,1D237;3E.3C=2AA5;3E.3E=226B,2A20;3E.3E.3E=22D9;3F=241,294,97D,13AE,A6EB;41=391,4"
    "10,13AA,15C5,A4EE,102A0,16F40;41.41=A732;41.45=C6,4D4;41.4F=A734;41.52=1F707;41.55=A736;41.56=A738,A"
    "73A;41.59=A73C;42=392,412,13F4,15F7,A4D0,A7B4,10282,102A1,10301;43=421,13DF,2CA4,A4DA,102A2,10302,10"
    "415,1051C,118E9,118F2,1F74C;43.27=187;44=13A0,15DE,15EA,A4D3;45=395,415,13AC,22FF,2D39,A4F0,10286,11"
    "8A6,118AE;46=3DC,15B4,A4DD,A798,10287,102A5,10525,118A2,118C2,1D213;47=50C,13C0,13F3,A4D6;47.27=193;"
    "48=397,41D,13BB,157C,2C8E,A4E7,102CF;4A=37F,408,13AB,148D,A4D9,A7B2;4B=39A,41A,13E6,16D5,2C94,A4D7,1"
    "0518;4B.27=198;4C=13DE,14AA,2CD0,A4E1,1041B,10526,118A3,118B2,16F16,1D22A;4D=39C,3FA,41C,13B7,15F0,1"
    "6D6,2C98,A4DF,102B0,10311;4D.42=1F76B;4E=39D,2C9A,A4E0,10513;4F=30,39F,41E,555,7C0,9E6,B20,B66,12D0,"
    "2C9E,2D54,3007,A4F3,10292,102AB,10404,104C2,10516,114D0,118B5,118E0;4F.27=13A4;4F.45=152;4F.4F=A698,"
    "A74E;50=3A1,420,13E2,146D,2CA2,A4D1,10295;50.27=1486;51=2D55;51.45=1F700;52=1A6,13A1,13D2,1587,A4E3,"
    "104B4,16F35,1D216;53=405,54F,13D5,13DA,A4E2,10296,10420,16F3A;54=3A4,422,13A2,22A4,27D9,2CA6,A4D4,10"
    "297,102B1,10315,118BC,16F0A,1F768;54.33=A728;55=54D,1200,144C,222A,22C3,A4F4,104CE,118B8,16F42;55.27"
    "=1467;56=474,667,6F7,13D9,142F,2D38,A4E6,A6DF,1051D,118A0,16F08,1D20D;56.42=1F76C;57=51C,13B3,13D4,A"
    "4EA,118E6,118EF;58=3A7,425,166D,16B7,2573,2CAC,2D5D,A4EB,A7B3,10290,102B4,10317,10322,10527,118EC;59"
    "=3A5,423,4AE,13A9,13BD,2CA8,A4EC,102B2,118A4,16F43;5A=396,13C3,A4DC,102F5,118A9,118E5;5C=2216,27CD,2"
    "9F5,29F9,31D4,4E36,1D20F,1D23B;5C.5C=244A,2CF9;5E=2C4,2C6;5F=7FA;61=251,3B1,430,237A;61.61=A733;61.6"
    "5=E6,4D5;61.6F=A735;61.75=A737;61.76=A739,A73B;61.79=A73D;62=184,42C,13CF,1472,15AF;62.27=1488;62.6C"
    "=42B;63=441,1D04,2CA5,ABAF,1043D;64=501,13E7,146F,A4D2;64.27=1487;64.7A=2A3;65=435,4BD,212E,AB32;66="
    "584,1E9D,A799,AB35;67=18D,261,581,1D83;68=4BB,570,13C2;69=131,269,26A,3B9,456,4CF,13A5,2373,A647,AB7"
    "5,118C3;6A=3F3,458;6C=31,49,7C,196,1C0,399,406,4C0,5C0,5D5,5DF,627,661,6F1,7CA,16C1,2223,23FD,2C92,2"
    "D4F,A4F2,1028A,10309,10320,16F28,1E8C7;6C.27=5F1;6C.4F=42E;6C.6C=1C1,5F0,2016,2225;6C.73=2AA;6C.74=2"
    "0B6;6C.7A=2AB;6E=578,57C;6F=3BF,3C3,43E,585,5E1,647,665,6BE,6C1,6D5,6F5,966,A66,AE6,BE6,C02,C66,C82,"
    "CE6,D02,D20,D66,D82,E50,ED0,101D,1040,10FF,1D0F,1D11,2C9F,AB3D,1042C,104EA,118C8,118D7;6F.65=153;6F."
    "6F=221E,A699,A74F;70=3C1,440,2374,2CA3;71=51B,563,566;72=433,1D26,2C85,AB47,AB48,AB81;72.27=491;72.6"
    "E=6D,11700,118E3;73=1BD,455,A731,ABAA,10448,118C1;73.73.73=1F75C;74.66=A777;74.73=2A6;75=28B,3C5,57D"
    ",1D1C,A79F,AB4E,AB52,104F6,118D8;75.65=1D6B;75.6F=AB63;76=3BD,475,5D8,1D20,2228,22C1,ABA9,11706,118C"
    "0;77=26F,461,51D,561,1D21,AB83,1170A,1170E,1170F;78=D7,445,1541,157D,166E,292B,292C,2A2F;79=263,28F,"
    "3B3,443,4AF,10E7,1D8C,1EFF,AB5A,118DC;7A=1D22,AB93,118C4;7B=2774,1D114;7D=2775;7E=2053,223C"
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
    return {"module": "yaml", "version": getattr(yaml, "__version__", None),
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
