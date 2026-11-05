#!/usr/bin/env bash
set -euo pipefail
# Run from repository root. No network, credentials, orders, or data collection.
pilot_root=${BT_PILOT_PRIVATE_ROOT:-/workspace/private-bt-data-pilot-v06}
prior_root=${BT_PILOT_V05_ROOT:-/workspace/private-bt-data-pilot-v05}
sec_root=${BT_PILOT_SEC_ROOT:-/workspace/private-bt-data-pilot-v03}
reviewed_src=${BT_PILOT_REVIEWED_SRC:-/workspace/Investment-System1/implementation/src}
python implementation/experiments/bt-data-pilot-v06/audit_v_ledger.py \
 --prices "$pilot_root/long-2016-20261030/restored" --sec "$sec_root" --prior "$prior_root" \
 --previous-sources "$pilot_root/pit-v-link" --abt-evidence "$pilot_root/continuation" \
 --reviewed-src "$reviewed_src" --sources "$pilot_root/v-ledger-audit" \
 --old-kis "$pilot_root/github-kis-cooldown-20261031/restored" \
 --pre2016 "$pilot_root/pre2016-2010/restored" \
 --calendar-fixture "$prior_root/github/gerrymanoim__exchange_calendars/tests__resources__xnys.csv" \
 --output "$pilot_root/v-ledger-audit/results"
python implementation/experiments/bt-data-pilot-v06/audit_period_extension.py \
 --root "$pilot_root" --prior "$prior_root" --output "$pilot_root/v-ledger-audit/results"
