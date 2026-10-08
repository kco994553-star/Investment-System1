// Deliberately fictional companies and labels; no classification of real holdings.
export function fictionalPortfolioFixture() {
  return {
    snapshot_id: 'fictional-composition-fixture-v1',
    portfolio_version: 'FICTIONAL_PORTFOLIO/1',
    qgv_version: 'NOT_APPLICABLE_FIXTURE',
    as_of: '2026-09-30T12:00:00Z',
    source: 'EXPLICIT_SYNTHETIC_FIXTURE',
    weight_basis: 'TARGET',
    data_kind: 'SYNTHETIC_FIXTURE',
    total_units: 100,
    cash_units: 10,
    type_catalog: ['Growth', 'Quality'],
    classification: {version: 'FICTIONAL_TAXONOMY/1', source: 'EXPLICIT_SYNTHETIC_FIXTURE', available_at: null},
    holdings: [
      {holding_id: 'fiction-a', security_id: null, label: 'Fictional A', weight_units: 40, industry: 'Fictional equipment', types: ['Growth', 'Quality']},
      {holding_id: 'fiction-b', security_id: null, label: 'Fictional B', weight_units: 25, industry: 'Fictional services', types: ['Growth']},
      {holding_id: 'fiction-c', security_id: null, label: 'Fictional C', weight_units: 15, industry: 'Fictional equipment', types: []},
      {holding_id: 'fiction-d', security_id: null, label: 'Fictional D', weight_units: 10, industry: null, types: null},
    ],
  };
}

export const portfolioFixture = fictionalPortfolioFixture;
