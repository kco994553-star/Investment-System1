#!/bin/bash
# v2-adversarial end-to-end: full FPIA CLI audit (523e702 sources, unmodified) of S24V2 = acaf1b5 + probe-a.yml
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-adversarial
T=3b09df4ebc32b517da1f4623ffd6c52cb1f35327
mkdir -p $W/full/out1
cd $W/repo
git rev-parse HEAD > $W/full/run1.verifier_head
git status --porcelain > $W/full/run1.verifier_status
date -u +%FT%TZ > $W/full/run1.start
$W/venv/bin/python implementation/tools/integration/track_c_fpia.py --repo $W/repo --tree $T \
  --register-commit f36292689eabf7ba3700d57a949fa0fb7343a2c6 --cdr CDR-014 \
  --out $W/full/out1/fpia_s24v2_run1.json --work-dir $W/full/work1 \
  > $W/full/run1.summary 2> $W/full/run1.stderr
echo $? > $W/full/run1.rc
date -u +%FT%TZ > $W/full/run1.end
