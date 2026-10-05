#!/bin/bash
# fix3 real CLI: S24V2 (round-2 end-to-end bypass, 3b09df4..., FPIA_PASS at 523e702) at the new head
C=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf17/fix3/cli
R=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf17/fix3/repo
until [ -f $C/AB.done ]; do sleep 20; done
T=$(git -C $R rev-parse v2adv/S24V2)
G=f36292689eabf7ba3700d57a949fa0fb7343a2c6
export PYTHONDONTWRITEBYTECODE=1
cd $R
date -u +%FT%TZ > $C/S.start
$C/../venv/bin/python implementation/tools/integration/track_c_fpia.py --repo $R --tree $T --register-commit $G --cdr CDR-014 \
  --out $C/out/fpia_s24v2.json --work-dir $C/workS > $C/S.summary 2> $C/S.stderr
echo $? > $C/S.rc; date -u +%FT%TZ > $C/S.end
$C/../venv/bin/python implementation/tools/integration/track_c_fpia.py --verify-output $C/out/fpia_s24v2.json > $C/S.verify 2>&1
echo done > $C/S.done
