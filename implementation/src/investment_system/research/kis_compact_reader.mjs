// Pure data-contract reference for Main. No fetch, DOM, price/scoring engine.
export function decodeRecord(packet, key) {
  const fail = () => { throw new Error('KIS_PACK_INVALID'); };
  if (packet?.schema !== 'kis-record-pack/2' || !Object.hasOwn(packet.rows, key)) fail();
  let nodes = 0; const active = new Set();
  function read(v, depth = 0) {
    if (++nodes >= 200000 || depth >= 100) fail();
    if (!Array.isArray(v)) return v;
    if (v[0] === 0) {
      const keys = Number.isInteger(v[1]) && packet.layouts[v[1]];
      if (v.length !== 3 || !Array.isArray(keys) || !Array.isArray(v[2]) ||
          keys.length !== v[2].length || new Set(keys).size !== keys.length) fail();
      return Object.fromEntries(keys.map((k, i) => [k, read(v[2][i], depth + 1)]));
    }
    if (v[0] === 1) {
      if (v.length !== 2 || !Array.isArray(v[1])) fail();
      return v[1].map(x => read(x, depth + 1));
    }
    const id = v[1];
    if (v[0] !== 2 || v.length !== 2 || !Number.isInteger(id) || id < 0 ||
        id >= packet.shared.length || active.has(id)) fail();
    active.add(id); const result = read(packet.shared[id], depth + 1); active.delete(id);
    return result;
  }
  return read(packet.rows[key]);
}
