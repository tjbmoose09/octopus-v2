// Octopus V2.2 — tiny `clsx`-shaped class joiner.
// We used to import `clsx` for this; dropped the dep since the feature set
// we actually use is ~6 lines. Mirrors the common API: pass strings,
// arrays, or { className: boolean } objects — any falsy value is skipped.
//
//   cx("a", cond && "b", { c: isC }, ["d", "e"])

export default function cx(...parts) {
  const out = [];
  for (const p of parts) {
    if (!p) continue;
    if (typeof p === "string" || typeof p === "number") {
      out.push(String(p));
    } else if (Array.isArray(p)) {
      const inner = cx(...p);
      if (inner) out.push(inner);
    } else if (typeof p === "object") {
      for (const k in p) if (p[k]) out.push(k);
    }
  }
  return out.join(" ");
}
