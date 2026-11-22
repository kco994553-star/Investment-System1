"""Offline replay. python macro-replay.py --input <retained-foundation> --output <directory>"""
import argparse
import hashlib
import itertools
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from lxml import html
from openpyxl import load_workbook

P = pd.Period
INDEX = pd.period_range("1946-01", "2025-12", freq="M")
DRAWS = 5000
BLOCK = 24
PERIODS = {"early": ("1948-01", "1999-12", "1999-12"),
           "test": ("2000-01", "2024-12", "2025-12")}
QUADS = ["G+I+", "G+I-", "G-I+", "G-I-", "tie"]


def read_bls(path, code):
    data = pd.read_csv(path, sep="\t", dtype=str)
    data.columns = data.columns.str.strip()
    rows = data[data.series_id.str.strip().eq(code) & data.period.str.fullmatch("M(0[1-9]|1[0-2])")]
    idx = pd.PeriodIndex(rows.year + "-" + rows.period.str[1:], freq="M")
    assert idx.is_unique
    return pd.Series(pd.to_numeric(rows.value.str.strip().replace("-", np.nan)).values, index=idx).reindex(INDEX)


def read_inputs(root):
    w = root / "warnings"
    u = read_bls(w / "bls_ln.src", "LNS14000000")
    c = read_bls(w / "bls_cu.src", "CUUR0000SA0")
    d = pd.read_csv(w / "bea.src")
    d = d[d.iloc[:, 0].eq("A191RL")]
    gdp = dict(zip(d.Period, d.Value))
    table = load_workbook(w / "rgdp.xlsx", read_only=True, data_only=True)["DATA"]
    first = {row[0].replace(":", ""): round(row[1], 1) for row in list(table.values)[5:]
             if isinstance(row[1], (int, float))}
    data = pd.read_csv(root / "regime" / "observations.csv")
    curve_data = data[data.series.eq("10Y3M_MEAN")]
    curve = pd.Series(curve_data.value.values, index=pd.PeriodIndex(curve_data.period, freq="M")).reindex(INDEX)

    recs = []
    for row in html.parse(str(w / "nber.src")).xpath("//table//tr"):
        months = []
        for cell in row.xpath("./td")[:2]:
            match = re.search(r"([A-Za-z]+ \d{4})\s*\(", cell.text_content())
            if match:
                months.append(P(datetime.strptime(match[1], "%B %Y"), freq="M"))
        if len(months) == 2 and months[0] >= P("1948-01"):
            recs.append(tuple(months))
    assert len(recs) == 12 and all(a < b for a, b in recs)

    # At decision month-end, the most recent available quarter ended in a prior month.
    qtr = [(m - 1).asfreq("Q") if (m - 1).month % 3 == 0 else (m - 1).asfreq("Q") - 1 for m in INDEX]
    def quarterly(series):
        values = pd.Series([series.get(str(q), np.nan) for q in qtr], index=INDEX)
        prev = pd.Series([series.get(str(q - 1), np.nan) for q in qtr], index=INDEX)
        return values, (values - prev).round(9)

    g, acc = quarterly(gdp)
    _, first_acc = quarterly(first)
    inf = (100 * (c / c.shift(12) - 1)).shift(1)
    inf_acc = (inf - inf.shift(3)).round(9)

    def quadrant(gacc):
        valid = gacc.notna() & inf_acc.notna()
        labels = np.select([gacc.gt(0) & inf_acc.gt(0), gacc.gt(0) & inf_acc.lt(0),
                            gacc.lt(0) & inf_acc.gt(0), gacc.lt(0) & inf_acc.lt(0)],
                           QUADS[:4], default="tie")
        return pd.Series(labels, index=INDEX).where(valid)

    u3 = u.rolling(3).mean()
    gap = (u3 - u3.shift(1).rolling(12).min()).shift(1).round(9)
    sahm = pd.Series(np.where(gap.ge(.5), "on", "off"), index=INDEX).where(gap.notna())
    slope = pd.Series(np.where(curve.lt(0), "inverted", "normal"), index=INDEX).where(curve.notna())
    rec = pd.Series(False, index=INDEX)
    onset = rec.copy()
    for peak, trough in recs:
        rec.loc[peak+1:trough] = True
        onset.at[peak+1] = True
    months = pd.DataFrame({"gdp_quarter": list(map(str, qtr)), "cpi_month": INDEX - 1,
                           "quadrant": quadrant(acc), "first_gdp_quadrant": quadrant(first_acc),
                           "sahm": sahm, "curve": slope}, index=INDEX)
    events = {"current_recession": (rec, 0)}
    for h in (3, 6, 12):
        def within(series):
            return pd.concat([series.shift(-i) for i in range(1, h + 1)], axis=1).max(axis=1, skipna=False)
        future_g = g.shift(-h)
        future_inf = inf.shift(-h)
        events.update({
            f"onset_{h}": (within(onset), h), f"recession_any_{h}": (within(rec), h),
            f"recession_at_{h}": (rec.shift(-h), h),
            f"gdp_negative_at_{h}": (future_g.lt(0).where(future_g.notna()), h),
            f"gdp_higher_at_{h}": ((future_g - g).round(9).gt(0).where(future_g.notna() & g.notna()), h),
            f"cpi_yoy_higher_at_{h}": ((future_inf - inf).round(9).gt(0).where(future_inf.notna() & inf.notna()), h)
        })
    return months, events, recs


class Bootstrap:
    """Paired circular moving blocks across calendar months; missing cells stay missing."""
    def __init__(self, n):
        self.n = n
        self.k, self.rem = divmod(n, BLOCK)
        rng = np.random.default_rng(20261122)
        self.starts = rng.integers(0, n, size=(DRAWS, self.k + bool(self.rem)))

    def sums(self, binary):
        v = np.asarray(binary, dtype=int)
        cum = np.r_[0, np.cumsum(np.r_[v, v[:BLOCK]])]
        a = self.starts[:, :self.k]
        sums = (cum[a + BLOCK] - cum[a]).sum(axis=1)
        if self.rem:
            b = self.starts[:, -1]
            sums += cum[b + self.rem] - cum[b]
        return sums


def summarize(mask, event, boot):
    ok = mask & event.notna()
    y = event.eq(True)
    n = ok.sum()
    successes = (ok & y).sum()
    starts = ok & ~ok.shift(fill_value=False)
    nruns = starts.sum()
    if not n:
        return None
    return n, successes, nruns, (starts & y).sum(), boot.sums(ok), boot.sums(ok & y)


def analyze(months, events):
    rows = []
    groups = [
        ("sahm", "sahm", ["on", "off"], ["current_recession"]),
        ("curve", "curve", ["inverted", "normal"], ["onset_12", "recession_at_12"]),
        ("curve_expansion", "curve", ["inverted", "normal"], ["onset_12"]),
        ("quadrant", "quadrant", QUADS, [f"{e}_{h}" for h in (3, 6, 12)
             for e in ("onset", "recession_any", "gdp_negative_at", "gdp_higher_at", "cpi_yoy_higher_at")])]
    q_events = groups[-1][-1]
    groups.extend([("quadrant_first", "first_gdp_quadrant", QUADS, q_events),
                   ("quadrant_revised_matched", "quadrant", QUADS, q_events)])
    for period, (first, last, followup) in PERIODS.items():
        sample = months.loc[first:last]
        boot = Bootstrap(len(sample))
        for group, feature, states, outcomes in groups:
            state = sample[feature]
            eligible_state = state.notna()
            if group in ("quadrant_first", "quadrant_revised_matched"):
                eligible_state &= sample.quadrant.notna() & sample.first_gdp_quadrant.notna()
            if group == "curve_expansion":
                eligible_state &= ~events["current_recession"][0].loc[sample.index]
            for event_name in outcomes:
                outcome, h = events[event_name]
                y = outcome.loc[sample.index].where(sample.index + h <= P(followup))
                base = summarize(eligible_state, y, boot)
                assert base is not None
                base_n, base_hits, _, _, base_ns, base_ys = base
                for label in states:
                    s = summarize(eligible_state & state.eq(label), y, boot)
                    n, hits, runs, runs_hit = s[:4] if s else (0, 0, 0, 0)
                    freq, delta, lo, hi, valid = [np.nan] * 5
                    if n:
                        freq = 100 * hits / n
                        delta = freq - 100 * base_hits / base_n
                        pick = (s[4] > 0) & (base_ns > 0)
                        valid = pick.mean()
                        if pick.any():
                            diff = 100 * (s[5][pick] / s[4][pick] - base_ys[pick] / base_ns[pick])
                            lo, hi = np.quantile(diff, [.025, .975])
                    rows.append(dict(period=period, family=group, state=label, outcome=event_name,
                        months=n, hits=hits, runs=runs, entry_hits=runs_hit,
                        rate_pct=freq, baseline_hits=base_hits, baseline_months=base_n,
                        baseline_pct=100*base_hits/base_n, difference_pp=delta,
                        block_lo_pp=lo, block_hi_pp=hi, valid_draw_pct=100*valid,
                        pass_screen=bool(n and freq >= 60 and lo > 0 and runs >= 5 and valid >= .95)))
    return pd.DataFrame(rows)


def dated_logs(months, events, recs):
    rec = events["current_recession"][0]
    cases = []
    starts = []
    for name, label in [("sahm", "on"), ("curve", "inverted")]:
        state = months[name].loc["1948-01":"2024-12"]
        m_on = state.eq(label)
        for flag, seq in itertools.groupby(zip(state.index, m_on), key=lambda t:t[1]):
            period = [m for m, _ in seq]
            if not flag:
                continue
            entry, end = period[0], period[-1]
            outcome = bool(rec.at[entry]) if name == "sahm" else bool(events["onset_12"][0].at[entry])
            within = [str(p + 1) for p, t in recs if
                      (entry <= t and end >= p+1 if name == "sahm" else entry < p+1 <= end+12 and end >= p+1-12)]
            starts.append(dict(signal=name, start=entry, end=end, months=len(period),
                        previous_state_known=bool(pd.notna(months[name].get(entry - 1))),
                        right_censored_at_cut=bool(end == P("2024-12")),
                        entry_hit=outcome, event_onsets_any_hit_in_spell="|".join(within)))
    for p, t in recs:
        onset = p+1
        active = months.sahm.loc[onset:t]
        sig = active[active.eq("on")]
        win = months.curve.loc[onset-12:onset-1]
        inv = win[win.eq("inverted")]
        cases.append(dict(onset=onset, trough=t, sahm_obs_months=active.count(), recession_months=len(active),
                first_active_in_recession=sig.index[0] if len(sig) else None,
                sahm_delay_from_onset=sig.index[0].ordinal-onset.ordinal if len(sig) else None,
                curve_obs_prior_12=win.count(), first_inversion_in_window=inv.index[0] if len(inv) else None,
                curve_lead_to_onset=onset.ordinal-inv.index[0].ordinal if len(inv) else None))
    return pd.DataFrame(cases), pd.DataFrame(starts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--private-audit", type=Path, help="Optional owner-only event timeline directory")
    args = ap.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    months, events, recs = read_inputs(args.input)
    stats = analyze(months, events)
    sensitivity = stats.family.isin(["quadrant_first", "quadrant_revised_matched"])
    stats.loc[~sensitivity].to_csv(out / "macro-frequencies.csv", index=False, float_format="%.4f")
    stats.loc[sensitivity].to_csv(out / "macro-vintage-frequencies.csv", index=False, float_format="%.4f")
    table, starts = dated_logs(months, events, recs)
    if args.private_audit:
        args.private_audit.mkdir(parents=True, exist_ok=True)
        table.to_csv(args.private_audit / "macro-events.csv", index=False)
        starts.to_csv(args.private_audit / "macro-entries.csv", index=False)
    monthly = months.loc["1948-01":"2024-12"].copy()
    monthly.to_csv(out / "macro-months.csv", index_label="month")
    files = ["warnings/" + f for f in ["bls_ln.src", "bls_cu.src", "bea.src", "rgdp.xlsx", "nber.src"]]
    files.append("regime/observations.csv")
    hashes = {f:hashlib.sha256((args.input / f).read_bytes()).hexdigest() for f in files}
    (out / "macro-input-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")


if __name__ == "__main__":
    main()
