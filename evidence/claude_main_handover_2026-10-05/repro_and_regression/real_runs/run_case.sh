#!/bin/bash
# v2-real: one FPIA CLI run, exactly as committed at the verifier checkout (no audit option changed;
# --work-dir only places the scrubbed work directory under this label, as in the 465354a/babf0a4 rounds).
# usage: run_case.sh <TREE> <LABEL> <REPO> <PYTHON>
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real
TREE=$1; LABEL=$2; REPO=$3; PY=$4
cd $W/repo
mkdir -p $W/out
rm -rf $W/work_$LABEL
O=$W/out/fpia_$LABEL
{ echo "verifier_head=$(git -C $W/repo rev-parse HEAD)"; echo "verifier_status_lines=$(git -C $W/repo status --porcelain | wc -l)";
  echo "repo=$REPO shallow=$(git -C $REPO rev-parse --is-shallow-repository) refs=$(git -C $REPO for-each-ref | wc -l)";
  echo "repo_refs_sha256=$(git -C $REPO for-each-ref --format='%(objectname) %(refname)' | sha256sum | cut -c1-64)";
  echo "tree=$TREE python=$PY"; } > $O.pre
CMD=("$PY" implementation/tools/integration/track_c_fpia.py --repo "$REPO" --tree "$TREE" \
  --register-commit f36292689eabf7ba3700d57a949fa0fb7343a2c6 --cdr CDR-014 --out "$O.json" \
  --work-dir "$W/work_$LABEL")
echo "cmd: (cwd $W/repo) ${CMD[*]}" >> $O.pre
date -u +%FT%TZ > $O.start; s=$(date +%s)
"${CMD[@]}" > $O.summary 2> $O.stderr
rc=$?
e=$(date +%s); date -u +%FT%TZ > $O.end
echo "exit=$rc wall_s=$((e-s))" >> $O.summary
ls -d $W/work_$LABEL 2>/dev/null && echo "work dir left behind" >> $O.summary
rm -rf $W/work_$LABEL
echo "post_verifier_status_lines=$(git -C $W/repo status --porcelain | wc -l)" >> $O.summary
"$PY" implementation/tools/integration/track_c_fpia.py --verify-output "$O.json" > $O.verify 2>&1
echo "verify_exit=$?" >> $O.verify
echo DONE $LABEL rc=$rc
