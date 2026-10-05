TCX = "track-c-evl-validation⠀"
S24V2 = ('name: "track-c-evl-validation\\u2800"\n'
         "on:\n  pull_request:\n  push:\n    branches: [feature/track-c-evl]\n  workflow_dispatch:\n"
         "permissions:\n  contents: read\n"
         "jobs:\n  validate:\n    runs-on: ubuntu-latest\n    steps:\n"
         "      - uses: actions/checkout@v4\n"
         "      - uses: actions/setup-python@v5\n        with:\n          python-version: \"3.11\"\n"
         "      - name: Install pytest\n        run: python -m pip install pytest==9.1.1 numpy==2.3.5\n"
         "      - name: PIT lineage Holdout cross-track audit and complete C6 evidence\n"
         "        run: cd ${{ github.workspace }}/implementation/tools && PYTHONPATH=../src:.. python track_c_c6_acceptance.py\n")
COMBINED = {"S24V2": {".github/workflows/probe-a.yml": S24V2}}
