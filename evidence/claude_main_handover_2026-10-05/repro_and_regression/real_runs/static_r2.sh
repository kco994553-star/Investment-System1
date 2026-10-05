#!/bin/bash
# v2-real static screen, resume round (r2): unmodified probe.py (Audit.run() of the verifier checkout with
# runtime/dynamic phases stubbed) on every spoof tree of variants/s_static.git (copied from wf15/v-adversarial,
# same static_variants.txt) plus acaf1b5 controls. Records the verifier commit and FPIA source blob ids.
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real
PY=$W/venv/bin/python
O=$W/probes/out_r2; mkdir -p $O
R=$W/repo
{ echo "date=$(date -u +%FT%TZ)"; echo "verifier_head=$(git -C $R rev-parse HEAD) status_lines=$(git -C $R status --porcelain | wc -l)";
  git -C $R ls-tree HEAD implementation/tools/integration/ | grep -E 'track_c_fpia' ;
  echo "probe.py sha256=$(sha256sum $W/probes/probe.py | cut -c1-64)";
  echo "mirror=$W/variants/s_static.git shallow=$(git -C $W/variants/s_static.git rev-parse --is-shallow-repository)"; } > $O/_header.txt
while read name sha; do
  (cd $W/probes && $PY probe.py $W/variants/s_static.git $sha $O/$name.json > $O/$name.out 2> $O/$name.err); echo "$name rc=$?" >> $O/_rc.txt
done < $W/variants/static_variants.txt
(cd $W/probes && $PY probe.py $W/repo acaf1b5a82859ac2750a130ebe88f8b4d272ac66 $O/P0_acaf1b5.json > $O/P0.out 2> $O/P0.err); echo "P0 rc=$?" >> $O/_rc.txt
(cd $W/probes && $PY probe.py $W/variants/rej.git acaf1b5a82859ac2750a130ebe88f8b4d272ac66 $O/R1_rejmirror_with_branch.json > $O/R1.out 2> $O/R1.err); echo "R1 rc=$?" >> $O/_rc.txt
echo "end=$(date -u +%FT%TZ) verifier_head_after=$(git -C $R rev-parse HEAD) status_lines=$(git -C $R status --porcelain | wc -l)" >> $O/_header.txt
rm -rf $W/probes/work/probe-*
