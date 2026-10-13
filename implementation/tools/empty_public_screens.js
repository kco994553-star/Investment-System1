'use strict';
// Serve the NOT_AVAILABLE public screens of an offline build (tools/fixtures/empty_public_screens.json) for tests that check
// the empty state, so they pass both on PR builds and on deploy builds that carry live public data.
const fs = require('node:fs');
const path = require('node:path');
const EMPTY = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/empty_public_screens.json'), 'utf8'));
// Live-only sidecars that offline builds do not publish at all: answer 404 like a PR build would.
const ABSENT = ['sec-public-inputs.json', 'sec-valuation-inputs.json', 'sec-universe-shares.json', 'sec-universe-qg.json', 'company-classification.json', 'sec-qgv2.json'];
async function routeEmptyPublicScreens(context) {
  for (const [name, body] of Object.entries(EMPTY)) {
    await context.route('**/' + name + '*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) }));
  }
  for (const name of ABSENT.filter((n) => !Object.hasOwn(EMPTY, n))) {
    await context.route('**/' + name + '*', (route) => route.fulfill({ status: 404, contentType: 'text/plain', body: 'not found' }));
  }
}
module.exports = { EMPTY, routeEmptyPublicScreens };
