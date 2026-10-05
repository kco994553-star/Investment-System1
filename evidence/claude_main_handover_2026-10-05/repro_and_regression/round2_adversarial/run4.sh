#!/bin/bash
# G5 isolation: identical to run1 except that the FPIA work directory lies under a symlinked TMPDIR
# (no --work-dir: FPIA's own tempfile.mkdtemp default, as on hosts whose TMPDIR is a symlink)
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-adversarial
T=3b09df4ebc32b517da1f4623ffd6c52cb1f35327
mkdir -p $W/full/out4 $W/det/realtmp
cd $W/repo
date -u +%FT%TZ > $W/full/run4.start
TMPDIR=$W/det/tmplink $W/venv/bin/python implementation/tools/integration/track_c_fpia.py --repo $W/repo --tree $T \
  --register-commit f36292689eabf7ba3700d57a949fa0fb7343a2c6 --cdr CDR-014 \
  --out $W/full/out4/fpia_s24v2_run4.json \
  > $W/full/run4.summary 2> $W/full/run4.stderr
echo $? > $W/full/run4.rc
date -u +%FT%TZ > $W/full/run4.end
