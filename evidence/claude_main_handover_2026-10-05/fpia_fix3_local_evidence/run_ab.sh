#!/bin/bash
# fix3 real CLI: acaf1b5 at the new head 11d2f25, (A) plain venv and explicit work dir; (B) the same venv reached
# through a symlinked path, FPIA's default work dir under a symlinked TMPDIR, another cwd and USER/LOGNAME.
C=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf17/fix3/cli
R=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf17/fix3/repo
T=acaf1b5a82859ac2750a130ebe88f8b4d272ac66
G=f36292689eabf7ba3700d57a949fa0fb7343a2c6
export PYTHONDONTWRITEBYTECODE=1
cd $R
date -u +%FT%TZ > $C/A.start
$C/../venv/bin/python implementation/tools/integration/track_c_fpia.py --repo $R --tree $T --register-commit $G --cdr CDR-014 \
  --out $C/out/fpia_acaf_A.json --work-dir $C/workA > $C/A.summary 2> $C/A.stderr
echo $? > $C/A.rc; date -u +%FT%TZ > $C/A.end
$C/../venv/bin/python implementation/tools/integration/track_c_fpia.py --verify-output $C/out/fpia_acaf_A.json > $C/A.verify 2>&1
cd $C/tmp-real
date -u +%FT%TZ > $C/B.start
env TMPDIR=$C/tmp-link USER=fpia-other LOGNAME=fpia-other $C/venvlink-dir/bin/python $R/implementation/tools/integration/track_c_fpia.py \
  --repo $R --tree $T --register-commit $G --cdr CDR-014 --out $C/out/fpia_acaf_B.json > $C/B.summary 2> $C/B.stderr
echo $? > $C/B.rc; date -u +%FT%TZ > $C/B.end
A=$(python3 -c "import json;print(json.load(open('$C/out/fpia_acaf_A.json'))['result_sha256'])")
$C/../venv/bin/python $R/implementation/tools/integration/track_c_fpia.py --verify-output $C/out/fpia_acaf_B.json --expect-result-sha256 $A > $C/B.verify 2>&1
echo done > $C/AB.done
