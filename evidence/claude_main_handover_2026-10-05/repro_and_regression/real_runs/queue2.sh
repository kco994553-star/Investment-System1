#!/bin/bash
# v2-real resume round: extra full CLI audit(s), strictly after queue.sh batches. usage: queue2.sh STAGE...
W=/tmp/claude-0/-home-user-Investment-System1/33fa0ec1-e143-560f-87b9-563dee3b3dc5/scratchpad/wf16/v2-real
PA=$W/venv/bin/python
MIR=$W/variants/s_static.git
S16=b33f20cb7fe984d993e429fddc2b6b27e958e79e
log() { echo "$(date -u +%FT%TZ) $*" >> $W/queue.log; }
disk() { df -h / | tail -1 >> $W/queue.log; }
for stage in "$@"; do
  log "BEGIN $stage"; disk
  case $stage in
    G) $W/run_case.sh $S16 c3_S16 $MIR $PA >> $W/queue.log 2>&1 ;;
  esac
  log "END $stage"; disk
done
