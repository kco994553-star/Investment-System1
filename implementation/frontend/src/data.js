// Public-data loader. The cockpit's own readers do the fetching and validation (PublicScreens, ClassificationScreens,
// Qgv2Inputs/SecQgv2, SecDisclosures, NewsSignals, DartDisclosures, ForwardValidation), so this app sees exactly what the
// cockpit sees: an invalid file is dropped by its reader and shows as NOT_AVAILABLE here. Nothing is stored or sent.

export const FILES = Object.freeze({
  qgv2: 'sec-qgv2.json',
  catalog: 'actual-catalog.json',
});

// Readers call view.fetch('<bare file name>'); the shim resolves names against the data base (default '../').
export function makeView(base, win = globalThis) {
  const prefix = String(base || '');
  return {
    fetch: (name, options) => win.fetch(prefix + name, options),
    AbortController: win.AbortController,
    SecQgv2: win.SecQgv2,
  };
}

export function dataBase(doc = globalThis.document) {
  const meta = doc && doc.querySelector('meta[name="data-base"]');
  const value = meta ? meta.getAttribute('content') : '../';
  // Only a same-origin relative base is accepted.
  return /^(\.\.\/|\.\/)*$/.test(value) ? value : '../';
}

async function json(view, name) {
  try {
    const r = await view.fetch(name, { cache: 'no-store', credentials: 'omit', redirect: 'error' });
    return r.ok ? await r.json() : null;
  } catch (_) {
    return null;
  }
}

const settle = async (promise) => {
  try {
    return await promise;
  } catch (_) {
    return null;
  }
};

// Loads every public input in parallel. Returns {base, screens, catalog, identities, disclosures, news, dart, ledger}.
// `screens` has the shape QgvScores.compute and MacroLights.merge expect (filename -> payload).
export async function loadAll(g = globalThis, base = dataBase(g.document)) {
  const view = makeView(base, g);
  const [screens, classification, qgv2, catalog, disclosures, news, dartDisclosures, dartFinancials, ledger] = await Promise.all([
    settle(g.PublicScreens ? g.PublicScreens.load(view) : null),
    settle(g.ClassificationScreens ? g.ClassificationScreens.load(view) : null),
    settle(g.Qgv2Inputs ? g.Qgv2Inputs.load(view) : null),
    json(view, FILES.catalog),
    settle(g.SecDisclosures ? g.SecDisclosures.load(view) : null),
    settle(g.NewsSignals ? g.NewsSignals.load(view) : null),
    settle(g.DartDisclosures ? g.DartDisclosures.load(view) : null),
    settle(g.DartDisclosures && g.DartDisclosures.loadFinancials ? g.DartDisclosures.loadFinancials(view) : null),
    settle(g.ForwardValidation ? g.ForwardValidation.load(view) : null),
  ]);
  const all = { ...(screens || {}) };
  if (classification && g.ClassificationScreens) all[g.ClassificationScreens.FILE] = classification;
  if (qgv2 && g.Qgv2Inputs) all[g.Qgv2Inputs.FILE] = qgv2;
  if (dartFinancials) all['dart-financials.json'] = dartFinancials;
  let identities = [];
  try {
    identities = catalog && g.DeviceWatchlist ? g.DeviceWatchlist.identities(catalog) : [];
  } catch (_) {
    identities = [];
  }
  return {
    base,
    screens: all,
    catalog: catalog && catalog.schema === 'DEVICE_ACTUAL_CATALOG/1' ? catalog : null,
    identities,
    disclosures: unwrap(disclosures),
    news: unwrap(news),
    dart: unwrap(dartDisclosures),
    ledger,
  };
}

// Reader results come either as the payload or as {state, payload}; keep the payload.
function unwrap(x) {
  if (!x || typeof x !== 'object') return null;
  if (x.payload && typeof x.payload === 'object') return x.payload;
  return x;
}
