import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Hypothesis keeps its storage (example database and the constants cache) in ./.hypothesis of the current directory by default,
# that is inside the checkout, where the private boundary scan (git ls-files --others) reads it as a not-yet-added file. Reuse the
# temporary storage path already given for the property tests (docs/research/TECHNICAL_PROPERTY_VALIDATION_20261105.md:
# HYPOTHESIS_STORAGE_DIRECTORY=/tmp/investment-technical-hypothesis), outside the checkout. Hypothesis reads it on first storage
# access, after this file loads. An explicit HYPOTHESIS_STORAGE_DIRECTORY is kept. The boundary scan itself is unchanged.
os.environ.setdefault("HYPOTHESIS_STORAGE_DIRECTORY", os.path.join(tempfile.gettempdir(), "investment-technical-hypothesis"))
