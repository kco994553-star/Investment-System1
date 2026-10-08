# Portable Chart preflight replay

This diagnostic successor uses fabricated owner claims and the preserved nine
case definitions. It never authenticates owner receipts or returns production
allocation. The four selected file pins include the original v0.7 archive.

Run from any location with the exact reviewed checkout bytes:

```sh
python -B /path/to/repo/implementation/experiments/chart-contract-v0.1/p0-diagnostic-repair-v0.8/replay_preflight_probes.py --repo /path/to/repo --output /tmp/new-chart-probes.json
```

The checkout must contain the pinned historical Git objects used by v0.6;
a shallow checkout missing them fails rather than replacing the baseline.
Output must be new and outside both selected and runner repositories.
Normal Python and -O enforce the same explicit runtime predicates.
CLOCK is the preserved historical fixture decision time, not current authority.
Read [HANDOFF.md](HANDOFF.md), [DIAGNOSTIC_INPUT_PINS.json](DIAGNOSTIC_INPUT_PINS.json)
and [PORTABLE_REVIEW.json](PORTABLE_REVIEW.json) for scope and actual verification.
Historical v0.6/v0.7 result files describe their original code, not this repair.
