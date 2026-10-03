# C3 metric conventions (EVL_METRICS_v1)

Scope: software calculations only; no numerical promotion threshold is chosen.
Regular-period decimal simple returns, explicit periods_per_year, one currency.
Upstream adapters own yield-to-period conversion, corporate actions, FX and trading
calendar alignment. Gaps/overlaps in the supplied timeline fail closed.

- Gross wealth compounds (1+r). Cost is an opening-equity fraction: net=r-cost.
- Real wealth compounds (1+net)/(1+realized inflation). Inflation is published by
  evaluation_time and used only for ex-post attribution, never model features.
- Risk-free-relative wealth compounds (1+net)/(1+rf). This is distinct from the
  arithmetic net-rf series used in the net view's Sharpe/Sortino calculations.
- Risk-free period return must have provenance/vintage available at period start;
  an annual quoted yield must not be passed as though it were a daily return.
- CAGR uses ending wealth ** (periods_per_year / n) - 1. Sharpe uses sample SD
  (ddof=1) and sqrt(annualization); Sortino uses RMS downside over all periods.
- Gross/net Sharpe and Sortino use arithmetic risk-free excess. Real and
  risk-free-relative view ratios use their own return series versus zero; these
  bases must not be silently compared as identical financial quantities.
- MDD is a nonnegative loss fraction from running peak, including initial wealth=1.
  Calmar=CAGR/MDD. Drawdown duration is counted in observed underwater periods;
  unrecovered_drawdown marks a right-censored episode, not a completed recovery.
- Downside capture uses the strategy/benchmark annualized returns restricted to
  benchmark-negative periods. No down periods yields None.
- Tail mean uses the worst ceil(n*tail_fraction) observations. Fraction is explicit
  and must be preregistered by the caller; this is a discrete empirical statistic,
  not a calibrated VaR confidence test or significance claim.
- Empty/nonfinite inputs fail. Undefined ratios are None with names in undefined;
  no fake zero/infinite score. A -100% loss is supported; below -100% is rejected.
- Outcome/benchmark provenance, RF vintage and inflation vintage are retained.
  Tax is always EXCLUDED; no tax parameter, live return or Official result added.

Primary formula references reviewed (no new dependency):
https://quantopian.github.io/empyrical/_modules/empyrical/stats.html
https://github.com/quantopian/empyrical/blob/master/empyrical/stats.py
Independent implementation uses Python math/statistics; hand-calculated fixtures
verify compounding, drawdown, sample variance, downside denominator and deflators.
