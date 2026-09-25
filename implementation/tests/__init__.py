# test package
import os
import tempfile

# Keep test runs from rewriting committed evidence under implementation/reports/
# (us_live / book / e2e default persistence paths honour this variable).
os.environ.setdefault("INVESTMENT_SYSTEM_REPORTS_DIR", tempfile.mkdtemp(prefix="is1_test_reports_"))
