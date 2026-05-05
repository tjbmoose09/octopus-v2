// Octopus V2.2 — Hacker Zone toggle badge.
// Lives in TopBar. Shift-click opens the bridge instead of flipping the
// zone (requires the orchestrator/hz_orchestrator bridge pair).

import { useZone } from "../hooks/useZone.jsx";
import { ZONES } from "../lib/theme";
import { Lock, Zap } from "lucide-react";

export default function ZoneBadge() {
  const { zone, setZone, bridgeOpen, openBridge, closeBridge, isHacker, theme } = useZone();

  function onClick(e) {
    if (e.shiftKey) {
      if (bridgeOpen) closeBridge();
      else openBridge("User shift-clicked zone badge");
      return;
    }
    setZone(isHacker ? ZONES.MAINLINE : ZONES.HACKER, "TopBar toggle");
  }

  return (
    <button
      onClick={onClick}
      title={
        isHacker
          ? "Hacker Zone active — click to return to Mainline • Shift-click to toggle bridge"
          : "Mainline — click to enter Hacker Zone • Shift-click to open bridge"
      }
      className="group relative flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs transition-all"
      style={{
        background: "var(--bg-2)",
        borderColor: isHacker ? theme.accent : "var(--line-2)",
        color: "var(--fg-0)",
        boxShadow: isHacker ? `0 0 14px -2px ${theme.glow}` : "none",
      }}
    >
      <span
        className="h-1.5 w-1.5 rounded-full anim-breathe"
        style={{ background: theme.nodeColor, boxShadow: `0 0 8px ${theme.glow}` }}
      />
      <span className="mono caps">{isHacker ? "HZ" : "MAINLINE"}</span>
      {bridgeOpen ? (
        <Zap size={12} style={{ color: "#ffb84a" }} />
      ) : (
        <Lock size={12} style={{ color: "var(--fg-3)" }} />
      )}
    </button>
  );
}
