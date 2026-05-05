// Octopus V2.2 — zone palette.
// Mirrors config/zones.py::ZONE_UI_THEME so TopBar / LogDrawer / sidebar
// can tint themselves without a round-trip. Keep in sync if you edit the
// Python side.

export const ZONES = Object.freeze({
  MAINLINE: "mainline",
  HACKER:   "hacker_zone",
});

export const ZONE_THEME = Object.freeze({
  mainline: {
    label:     "Mainline Mesh",
    nodeColor: "#00e5ff",
    edgeColor: "#4e6fff",
    glow:      "#00e5ff66",
    accent:    "#00e5ff",
    surface:   "#0a0e17",
  },
  hacker_zone: {
    label:     "Hacker Zone",
    nodeColor: "#ff2d7a",
    edgeColor: "#7a00ff",
    glow:      "#ff2d7a55",
    accent:    "#ff2d7a",
    surface:   "#120616",
  },
});

export function themeFor(zone) {
  return ZONE_THEME[zone] || ZONE_THEME.mainline;
}

// Maps an event kind → (label, dot-color, icon-name). Used by the
// ChangesRenderer + LogDrawer for consistent glyphing.
export const EVENT_KIND = Object.freeze({
  plan:         { label: "Plan",         color: "#9a7dff", icon: "ListChecks" },
  routing:      { label: "Route",        color: "#00e5ff", icon: "Share2" },
  file_diff:    { label: "File change",  color: "#3ce28f", icon: "FileDiff" },
  memory_write: { label: "Memory",       color: "#ffb84a", icon: "Database" },
  command:      { label: "Command",      color: "#ff8a3d", icon: "Terminal" },
  bridge:       { label: "Bridge",       color: "#ff2d7a", icon: "Radio" },
  reply:        { label: "Reply",        color: "#e6f2ff", icon: "MessageSquare" },
  // Cursor-style status signals (not persisted by engine, emitted by UI)
  thinking:     { label: "Thought",      color: "#9a7dff", icon: "Brain" },
  reading:      { label: "Read",         color: "#6fb3ff", icon: "BookOpen" },
});

export function kindMeta(kind) {
  return EVENT_KIND[kind] || { label: kind, color: "#8aa0c0", icon: "Circle" };
}
