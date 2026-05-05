// Octopus V2.2 — ZoneProvider + useZone hook.
// Owns the session's zone state on the frontend; mirrors / syncs with
// the backend SessionZoneState via POST /api/session/zone.

import { createContext, useContext, useEffect, useMemo, useState, useCallback } from "react";
import { ZONES, themeFor } from "../lib/theme";
import { API } from "../lib/api";

const ZoneCtx = createContext(null);
const STORAGE_KEY = "octopus-v2.zone";

export function ZoneProvider({ children }) {
  const [zone, setZoneState] = useState(() => {
    try { return localStorage.getItem(STORAGE_KEY) || ZONES.MAINLINE; }
    catch (_) { return ZONES.MAINLINE; }
  });
  const [bridgeOpen, setBridgeOpen] = useState(false);

  // Sync <html data-zone="..."> every time zone flips; CSS tokens in
  // index.css watch this attribute and retint the whole surface.
  useEffect(() => {
    document.documentElement.setAttribute("data-zone", zone);
    try { localStorage.setItem(STORAGE_KEY, zone); } catch (_) {}
  }, [zone]);

  const setZone = useCallback(async (next, reason) => {
    const z = next === ZONES.HACKER ? ZONES.HACKER : ZONES.MAINLINE;
    setZoneState(z);
    // Fire-and-forget; UI never blocks on the zone toggle.
    try {
      await API.sessionZone(z === ZONES.HACKER, reason);
    } catch (_) { /* drawer will log the failure */ }
  }, []);

  const openBridge = useCallback(async (reason) => {
    setBridgeOpen(true);
    try { await API.openBridge(reason); } catch (_) {}
  }, []);

  const closeBridge = useCallback(async () => {
    setBridgeOpen(false);
    try { await API.closeBridge(); } catch (_) {}
  }, []);

  const theme = useMemo(() => themeFor(zone), [zone]);

  const value = useMemo(
    () => ({ zone, setZone, theme, bridgeOpen, openBridge, closeBridge, isHacker: zone === ZONES.HACKER }),
    [zone, setZone, theme, bridgeOpen, openBridge, closeBridge]
  );

  return <ZoneCtx.Provider value={value}>{children}</ZoneCtx.Provider>;
}

export function useZone() {
  const ctx = useContext(ZoneCtx);
  if (!ctx) throw new Error("useZone must be used inside <ZoneProvider>");
  return ctx;
}
