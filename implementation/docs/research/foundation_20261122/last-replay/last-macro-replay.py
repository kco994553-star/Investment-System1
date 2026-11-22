"""Research replay using archived local inputs; see last-macro-ko.md for invocation."""
import argparse
import hashlib
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

P = pd.Period
PERIODS = {"all": ("1948-01", "2024-12", "2025-12"),
           "selection": ("1948-01", "1999-12", "1999-12"),
           "test": ("2000-01", "2024-12", "2025-12")}
HORIZONS = (6, 12, 18, 24)


def earlier_module(path):
    spec = importlib.util.spec_from_file_location("earlier_replay", path / "macro-replay.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_states(prior, source, nyfed):
    months, _, cycles = prior.read_inputs(source)
    unemployment = prior.read_bls(source / "warnings" / "bls_ln.src", "LNS14000000")
    first = unemployment.first_valid_index()
    # The implementation requires 3 consecutive observations, 12 months of elapsed
    # history and uses the observed single-month minimum inside that fixed window.
    u3 = unemployment.rolling(3).mean()
    minimum = unemployment.rolling(12, min_periods=1).min().where(unemployment.index >= first + 11)
    gap = (u3 - minimum).shift(1)
    official = (gap >= .5 - 1e-9).where(gap.notna()).astype("boolean")
    def status(col, label):
        return months[col].eq(label).where(months[col].notna()).astype("boolean")
    states = {"employment_v1": official, "sahm": status("sahm", "on"),
              "treasury": status("curve", "inverted")}
    if nyfed:
        import xlrd
        expected = "2fe39a1698a8c58e49180fafaf4bd3fb4afaf8a1ac587408a7760d7a9ba6035f"
        if hashlib.sha256(nyfed.read_bytes()).hexdigest() != expected:
            raise ValueError("NY Fed workbook differs from the archived research vintage")
        workbook = xlrd.open_workbook(nyfed)
        sheet = workbook.sheet_by_name("rec_prob")
        assert sheet.row_values(0)[:5] == ["Date", "10 Year Treasury Yield", "3 Month Treasury Yield",
                                           "3 Month Treasury Yield (Bond Equivalent Basis)", "Spread"]
        rates = {}
        for i in range(1, sheet.nrows):
            serial, ten, discount, equivalent, spread = sheet.row_values(i)[:5]
            if [ten, discount, equivalent, spread] == [""] * 4:
                continue
            assert abs(ten - equivalent - spread) < 1e-10
            month = P(xlrd.xldate_as_datetime(serial, workbook.datemode), freq="M")
            assert month not in rates
            rates[month] = spread
        assert len(rates) == len(pd.period_range(min(rates), max(rates), freq="M")) == 814
        s = pd.Series(rates).reindex(months.index)
        states["nyfed"] = (s < 0).where(s.notna()).astype("boolean")
    return states, cycles


def spells(state):
    starts = state.fillna(False) & ~state.shift().fillna(False)
    ends = state.fillna(False) & ~state.shift(-1).fillna(False)
    return [(start, end, pd.notna(state.get(start - 1)))
            for start, end in zip(state.index[starts], state.index[ends], strict=True)]


def labels(index, cycles, h):
    # Event IDs give multiple signals for one recession exactly one unique ID.
    event = pd.Series("", index=index)
    for p, trough in cycles:
        onset = p + 1
        valid = ((index <= trough) & (index >= onset)) if h == 0 else (
                (index < onset) & (index + h >= onset))
        event.loc[valid] = event.loc[valid].apply(lambda value: (value + "|" if value else "") + str(onset.year))
    return event


def event_ids(series):
    return {x for value in series for x in value.split("|") if x}


def pct(a, b):
    return 100 * a / b if b else np.nan


def delta_interval(boot, ok, event, on):
    a, b, c, d = (boot.sums(x) for x in (on & event, on, ok & event, ok))
    have = (b > 0) & (d > 0)
    if not have.any():
        return np.nan, np.nan, 0.
    low, high = np.quantile(100 * (a[have]/b[have] - c[have]/d[have]), [.025, .975])
    return low, high, 100 * have.mean()


def episode_rows(name, state, cycles):
    curve = name in ("nyfed", "treasury")
    records = []
    for start, end, observed in spells(state):
        if not P("1948-01") <= start <= P("2024-12"):
            continue
        end = min(end, P("2024-12"))
        fields = dict(signal=name, first_on=str(start), last_on=str(end), on_months=end.ordinal-start.ordinal+1,
                      confirmed_off_before=int(observed))
        horizons = HORIZONS if curve else (0,)
        for h in horizons:
            if start+h > P("2025-12"):
                fields[f"entry_h{h}"] = "censored"
            else:
                ids = event_ids(labels(pd.PeriodIndex([start]), cycles, h))
                fields[f"entry_h{h}"] = "|".join(sorted(ids)) if ids else "miss"
        if curve:
            future = [p+1 for p, _ in cycles if start < p+1 <= start+24 and p+1 <= P("2025-12")]
            fields["months_to_next_onset_within_24"] = future[0].ordinal-start.ordinal if future else None
        else:
            current = [p+1 for p, t in cycles if p+1 <= start <= t]
            fields["months_after_onset_if_current"] = start.ordinal-current[0].ordinal if current else None
        records.append(fields)
    return records


def group_stats(name, state, cycles, prior, common_window=False, periods=PERIODS):
    out = []
    all_spells = spells(state)
    curve = name in ("nyfed", "treasury")
    for label, (first, last, censor) in periods.items():
        z = state.loc[first:last]
        boot = prior.Bootstrap(len(z))
        for h in HORIZONS if curve else (0,):
            needed = max(HORIZONS) if common_window else h
            ok = z.notna() & (z.index + needed <= P(censor))
            event = labels(z.index, cycles, h)
            yes = event.ne("")
            on = ok & z.fillna(False)
            E = [start for start, _, observed in all_spells if observed and start in z.index and ok.at[start]]
            entries = event.loc[E]
            eligible_ids = event_ids(event.loc[ok])
            hit_ids = event_ids(entries)
            observable_spells = []
            for a, b, observed in all_spells:
                overlap = on.loc[a:b]
                if overlap.any():
                    observable_spells.append((observed, a, event.loc[overlap.index[overlap]]))
            any_hit = sum(s.ne("").any() for _, _, s in observable_spells)
            lb, ub, valid = delta_interval(boot, ok, yes, on)
            base = pct((ok & yes).sum(), ok.sum())
            frequency = pct((on & yes).sum(), on.sum())
            passed = bool(frequency >= 60 and lb > 0 and len(observable_spells) >= 5 and valid >= 95)
            out.append(dict(signal=name, sample=label, horizon_months=h, eligible_months=int(ok.sum()),
                    baseline_event_months=int((ok & yes).sum()), baseline_pct=base,
                    active_months=int(on.sum()), active_hit_months=int((on & yes).sum()),
                    monthly_pct=frequency, delta_pp=frequency-base, block_low_pp=lb, block_high_pp=ub,
                    valid_bootstrap_pct=valid, monthly_pass_screen=passed,
                    active_spells=len(observable_spells), any_month_hit_spells=any_hit,
                    confirmed_entries=len(E), hit_entries=int(entries.ne("").sum()),
                    missed_entries=int(entries.eq("").sum()), entry_pct=pct(entries.ne("").sum(),len(E)),
                    reached_unique_recessions=len(hit_ids), available_unique_recessions=len(eligible_ids),
                    active_month_unique_recessions=len(event_ids(event.loc[on])),
                    miss_recession_onset_years="|".join(sorted(eligible_ids-hit_ids)),
                    hit_recession_onset_years="|".join(sorted(hit_ids)),
                    data_months_censored=int((z.notna() & ~ok).sum())))
    return out


def employment_comparison(states, cycles):
    output = []
    for name, (first,last,_) in PERIODS.items():
        a, b = states["employment_v1"].loc[first:last], states["sahm"].loc[first:last]
        ok = a.notna() & b.notna()
        ref = labels(a.index, cycles, 0).ne("")
        output.append(dict(sample=name, comparable_months=int(ok.sum()), differing_months=int((ok & (a!=b)).sum()),
                   both_on=int((ok & a & b).sum()), v1_only_on=int((ok & a & ~b).sum()),
                   sahm_only_on=int((ok & ~a & b).sum()),
                   v1_only_current_recession=int((ok & a & ~b & ref).sum()),
                   sahm_only_current_recession=int((ok & ~a & b & ref).sum())))
    return output


def peak_comparison(states, cycles):
    """Prior benchmark for timing: nearest unused OFF→ON in -3..+6 months of NBER peak."""
    output = []
    for name in ("employment_v1", "sahm"):
        state = states[name]
        actual = [a for a, _, observed in spells(state) if observed]
        for sample, (first, last, _) in PERIODS.items():
            used = set()
            matches = []
            lags = []
            after_trough = 0
            for peak, trough in cycles:
                if not P(first) <= peak <= P(last):
                    continue
                candidates = [a for a in actual if a not in used and peak-3 <= a <= peak+6]
                if candidates:
                    choice = min(candidates, key=lambda a: (abs(a.ordinal - peak.ordinal), a))
                    used.add(choice)
                    matches.append(str((peak + 1).year))
                    lags.append(choice.ordinal - peak.ordinal)
                    after_trough += int(choice > trough)
            output.append(dict(signal=name, sample=sample, benchmark_peaks=sum(
                    P(first) <= peak <= P(last) for peak, _ in cycles), matched_peaks=len(used),
                    matches_after_trough=after_trough, median_lag_from_peak=np.median(lags) if lags else None,
                    matched_onset_years="|".join(matches)))
    return output


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--previous", required=True, type=Path, help="Directory containing #598's macro-replay.py")
    ap.add_argument("--nyfed", type=Path, help="Optional local archived official allmonth.xls")
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    prior = earlier_module(args.previous)
    states, cycles = local_states(prior, args.input, args.nyfed)
    summaries, episodes, fixed = [], [], []
    for name, series in states.items():
        summaries.extend(group_stats(name, series, cycles, prior))
        episodes.extend(episode_rows(name, series, cycles))
        if name in ("nyfed", "treasury"):
            fixed.extend(group_stats(name, series, cycles, prior, common_window=True))
        if name == "nyfed":
            periods = {"from_1962": ("1962-01", "2024-12", "2025-12"),
                       "selection_from_1962": ("1962-01", "1999-12", "1999-12")}
            summaries.extend(group_stats(name, series, cycles, prior, periods=periods))
    args.output.mkdir(exist_ok=True, parents=True)
    for fname, records in [("last-macro-summary", summaries), ("last-macro-episodes", episodes),
                           ("last-curve-common-months", fixed),
                           ("last-employment-peak-matching", peak_comparison(states, cycles)),
                           ("last-employment-comparison", employment_comparison(states, cycles))]:
        pd.DataFrame(records).to_csv(args.output / f"{fname}.csv", index=False, float_format="%.4f")


if __name__ == "__main__":
    main()
