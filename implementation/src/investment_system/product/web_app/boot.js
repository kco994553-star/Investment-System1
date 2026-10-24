/* Starts the new frontend after every screen has registered: draws the shell first, then loads the old modules and the P1 layer
   after its first paint (loader.js; owner 2026-10-24, P2-1a). */
window.IS2.start();
// Without loader.js (it failed to load) there is no load(): the shell already shows the failure notice.
if(typeof window.IS2.load==='function')window.IS2.load();
