#!/bin/bash
# v2-real: full CLI audits, strictly one at a time. usage: queue.sh STAGE [STAGE...]
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real
PA=$W/venv/bin/python
PB=$W/alt/elsewhere/venv-b/bin/python
REPO=$W/repo
MIR=$W/variants/s_static.git
ACAF=acaf1b5a82859ac2750a130ebe88f8b4d272ac66
B9=b9e01a976a0e9efcd1f2d3a5d3503d2795cc5565
S24=14c5a8bee76a8f35de09c76a4775c7de3d7bd506
S1=8b924a26c9008db9891f5c804e093e155ed31992
log() { echo "$(date -u +%FT%TZ) $*" >> $W/queue.log; }
disk() { df -h / | tail -1 >> $W/queue.log; }
for stage in "$@"; do
  log "BEGIN $stage"; disk
  case $stage in
    A) $W/run_case.sh $ACAF c1_acaf1b5_A $REPO $PA >> $W/queue.log 2>&1 ;;
    B) $W/run_case.sh $ACAF c5_acaf1b5_B $REPO $PB >> $W/queue.log 2>&1 ;;
    C) $W/run_case.sh $B9 c2_b9e01a9 $REPO $PA >> $W/queue.log 2>&1 ;;
    D) $W/run_case.sh $S24 c3_S24 $MIR $PA >> $W/queue.log 2>&1 ;;
    E) $W/run_case.sh $S1 c3_S1 $MIR $PA >> $W/queue.log 2>&1 ;;
    F) git -C $REPO branch feature/rejected-ideas $ACAF >> $W/queue.log 2>&1
       git -C $REPO for-each-ref refs/heads --format='%(objectname) %(refname)' >> $W/queue.log
       $W/run_case.sh $ACAF c4_rejected_ideas $REPO $PA >> $W/queue.log 2>&1
       git -C $REPO branch -D feature/rejected-ideas >> $W/queue.log 2>&1
       git -C $REPO for-each-ref refs/heads --format='%(objectname) %(refname)' >> $W/queue.log ;;
  esac
  log "END $stage"; disk
done
