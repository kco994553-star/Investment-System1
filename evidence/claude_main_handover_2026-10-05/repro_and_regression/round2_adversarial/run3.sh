#!/bin/bash
# G5 isolation: identical to run1 except that the verifier interpreter is invoked through a symlinked venv path
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-adversarial
T=3b09df4ebc32b517da1f4623ffd6c52cb1f35327
mkdir -p $W/full/out3
cd $W/repo
date -u +%FT%TZ > $W/full/run3.start
$W/det/venvlink/bin/python implementation/tools/integration/track_c_fpia.py --repo $W/repo --tree $T \
  --register-commit f36292689eabf7ba3700d57a949fa0fb7343a2c6 --cdr CDR-014 \
  --out $W/full/out3/fpia_s24v2_run3.json --work-dir $W/full/work3 \
  > $W/full/run3.summary 2> $W/full/run3.stderr
echo $? > $W/full/run3.rc
date -u +%FT%TZ > $W/full/run3.end
