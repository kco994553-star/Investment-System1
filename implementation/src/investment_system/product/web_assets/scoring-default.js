/* The single scoring-default setting (GSQ-022, 2026-10-13, pending approval). 'v1' | 'v2'. Every score consumer (S04, S05 factor
   tabs, S06 leaderboard, virtual-trading judgement inputs, daily report and its export) reads scores through QgvScores, which
   reads only this value. Stays 'v1' until the user approves the GSQ-022 26E record; flipping it to 'v2' flips every consumer. */
(function(r){const d=Object.freeze({scoring_default:'v1'});if(typeof module==='object'&&module.exports)module.exports=d;else r.ScoringDefault=d;})(globalThis);
