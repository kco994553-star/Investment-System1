# Independent CDR-012 reference oracle (persisted copy)

Written by the Primary Integration Writer before Codex's CDR-012 repair existed (GIE-011a). It is the independent oracle used to verify #31 `c9e0fa7` (GIE-011) and the #40 tree. Persisted here so the CDR-014 §12 oracle replay can be repeated on future merge-result SHAs.

Restore:

1. Copy this directory, rename every `*.py.txt` / `*.sh.txt` back to `*.py` / `*.sh`, and `gunzip -k expected_cdr012.json.gz expected_cdr010.json.gz`.
2. Check `sha256sum -c SHA256SUMS` for the files present (the original also listed scratch-only files such as `selftest*/`, which are not persisted) and `sha256sum -c EXPECTED_UNCOMPRESSED_SHA256`.
3. Create a Python 3.11 venv with `numpy==2.3.5`, `scipy`, `pytest==9.1.1`; provide `src_b9e01a9/implementation/src` from `git archive b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565 implementation/src`.
4. Follow `README.md` (compare_cdr012.py with the strict mapping `--not-run-reason-regex '^all bootstrap replicates degenerate$'`, and registry_probe_cdr012.py).

Key hashes: `oracle_cdr012.py` efcbf2ea…, `compare_cdr012.py` 02809638…, `expected_cdr012.json` d98fae60…, `expected_cdr010.json` 2b646b3d….
