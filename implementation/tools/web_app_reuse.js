'use strict';
// New frontend P1 helper (not a test): the one place that knows where the old modules live and which of them the new
// frontend reuses. Plan A (tools/build_web_app.py): web_app/index.html is the reuse list; a script it loads that has no file
// of that name in web_app is an old web_assets file kept byte-identical by the build. When the old modules move into web_app
// (P3), OLD below is the only line node tests need changed.
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');
const PRODUCT = path.join(ROOT, 'implementation/src/investment_system/product');
const OLD = path.join(PRODUCT, 'web_assets');
const NEW = path.join(PRODUCT, 'web_app');

const isFile = (p) => fs.existsSync(p) && fs.statSync(p).isFile();
// <script src> values of a page in document order (comments skipped). Inline scripts are reported as '' so callers can fail.
function scriptsOf(html) {
  const text = String(html).replace(/<!--[\s\S]*?-->/g, '');
  return [...text.matchAll(/<script\b([^>]*)>/gi)].map((m) => { const src = /\bsrc="([^"]*)"/i.exec(m[1]); return src ? src[1] : ''; });
}
const newIndex = () => fs.readFileSync(path.join(NEW, 'index.html'), 'utf8');
const oldIndex = () => fs.readFileSync(path.join(OLD, 'index.html'), 'utf8');
// The new page's scripts, and the old page's scripts in first-load order (the old page loads two playbook files twice).
const scripts = () => scriptsOf(newIndex());
const oldScripts = () => [...new Set(scriptsOf(oldIndex()))];
// Same rule as build_web_app.reused_old_files: web_app wins on a shared name, otherwise the file must be in web_assets.
function reused(list = scripts()) {
  return list.filter((src) => {
    if (isFile(path.join(NEW, src))) return false;
    if (!isFile(path.join(OLD, src))) throw new Error('REUSE_MISSING ' + src);
    return true;
  });
}
const oldPath = (name) => path.join(OLD, name);
const requireOld = (name) => require(oldPath(name));
const newPath = (name) => path.join(NEW, name);
const requireNew = (name) => require(newPath(name));

module.exports = Object.freeze({ ROOT, OLD, NEW, scriptsOf, newIndex, oldIndex, scripts, oldScripts, reused, oldPath, requireOld, newPath, requireNew });
