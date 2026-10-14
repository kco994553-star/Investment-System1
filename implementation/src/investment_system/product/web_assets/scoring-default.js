/* The single scoring-default setting (GSQ-022, approved 2026-10-13): v2 is the default. Owner decision 2026-10-14: QGV v2 is the
   ONLY score on screens. Every score consumer (S04/S05 company screens, S06 leaderboard, virtual-trading judgement inputs, the
   daily report and its export) reads scores through QgvScores, which shows v2 or the v2 NOT_AVAILABLE reason and never falls
   back to v1 ('임시 기본', 'v1 비교용' and '[자세히] v1 참고' were removed). v1 survives only in the forward-validation ledger
   comparison record. PLAYBOOK_V1 §13-11: v2_since is the strategy-version switch date (one line). No backfill. */
(function(r){const d=Object.freeze({scoring_default:'v2',v2_since:null});if(typeof module==='object'&&module.exports)module.exports=d;else r.ScoringDefault=d;})(globalThis);
