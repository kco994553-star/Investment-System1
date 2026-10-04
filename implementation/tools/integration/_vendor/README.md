# Vendored third-party code for the Track C FPIA tools

`yaml/` is the pure-Python part of **PyYAML 6.0.1** (MIT licence, `yaml/LICENSE`), copied byte for
byte from `lib/yaml/` of the upstream source distribution `PyYAML-6.0.1.tar.gz` (PyPI, sha256
`bfdf460b1736c775f2ba9f6a92bca30bc2095067b8a9d77876d1fad6cc3b4a43`).

Why it is vendored: `track_c_fpia_workflows.py` reads workflow files with `yaml.safe_load` and
`yaml.compose(Loader=yaml.SafeLoader)` (AC-32.spoof). The owner full-suite workflows install only pytest
and numpy, so an installed PyYAML cannot be assumed wherever the FPIA tests run. Importing this copy
also keeps the loader identical in every environment, whatever PyYAML (if any) is installed.

One upstream file is left out: `cyaml.py`. It imports the compiled `yaml._yaml` (libyaml) by absolute
name, which would bind this copy to whatever PyYAML is installed. Without it, upstream
`__init__.py` falls back on its own `ImportError` branch (`__with_libyaml__ = False`); the FPIA uses only
the pure-Python `SafeLoader`. Nothing else was changed, added or removed. No bytecode is committed.

sha256 of each vendored file (equal to the upstream file of the same name):

```
8d3928f9dc4490fd635707cb88eb26bd764102a7282954307d3e5167a577e8a4  LICENSE
6e1974e6a49e3bed59c654918c6aef9769bd9eb5dbd67f7e1906ad4cdd0caea7  __init__.py
fcaa37d16afa783594794a5ab94193dcb720f503c19ce3d59539c8311189f453  composer.py
90d8247da78b524c10618fd0e857f54f3d97570fe91b5c5513d024ef3faf88b0  constructor.py
3cb72d66563064ba7b5e679477046ebf89d8399d940670c8532f3e94a7cb17ea  dumper.py
8e086d694ede170837d5b1b407b45979aff6f40762f422a65eafd08e04290a44  emitter.py
021f73fada072546c4f63f8cf18a7181244ce4280b09cc15cc980b2d1176171a  error.py
e74fd392c810884e2ea7e94aa3f57e9c1cbeb402319083d0c58e6a0e1282787c  events.py
5156becc8aa6905482218abf3e04869b835226db4763645fff3438fdbd5f1cdd  loader.py
80f28d8fca4a09d87677882bde021820d9cf39a3b11a12405226211919cf13ce  nodes.py
8a55a9e6fbe0a07146cef3990c8b45a068c3e83e369e1959ad9ca30306b4a09a  parser.py
d1d9b38ab3a20c6e17a38d519ee412ecaf6b918df18c78956ac7c330d4ea08dc  reader.py
22e58ff9c016f6c1ca1274b4802a926bcf78935060e1c813c5a0f021c6d143e6  representer.py
f4bf9561f9b89961f1503d558385fbae30d12bfed565de9bf76c33abb63620a6  resolver.py
60433788b652690c17710460da5d91e0c753d3318fd85f5e1e42862a71f25906  scanner.py
0a1b85826854d35863e31808f0668abfabdf33606e8f06bd8bb7761401e3edc0  serializer.py
953408cd2570f0c83dc2fe39f7e4e388e41eeb05738aa69196a5f6ffcf6ba79e  tokens.py
```
