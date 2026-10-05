#!/bin/bash
# G5 determinism: second full audit of the same T (S24V2) and the same verifier (523e702), perturbed:
# interpreter via a symlinked venv path, TMPDIR = a symlink (FPIA's default mkdtemp work dir, no --work-dir),
# another cwd, PYTHONHASHSEED=7, TZ=Asia/Seoul, umask 027, USER/LOGNAME=runner in the parent environment.
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-adversarial
T=3b09df4ebc32b517da1f4623ffd6c52cb1f35327
mkdir -p $W/full/out2 $W/det/realtmp
cd $W/det
umask 027
date -u +%FT%TZ > $W/full/run2.start
env PYTHONHASHSEED=7 TZ=Asia/Seoul USER=runner LOGNAME=runner TMPDIR=$W/det/tmplink \
  $W/det/venvlink/bin/python $W/repo/implementation/tools/integration/track_c_fpia.py --repo $W/repo --tree $T \
  --register-commit f36292689eabf7ba3700d57a949fa0fb7343a2c6 --cdr CDR-014 --out $W/full/out2/fpia_s24v2_run2.json \
  > $W/full/run2.summary 2> $W/full/run2.stderr
echo $? > $W/full/run2.rc
date -u +%FT%TZ > $W/full/run2.end
