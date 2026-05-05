// Octopus V2.2 — App shell.
// Mounts the ZoneProvider (already wrapped in main.jsx), wires the v6
// router and assembles the persistent chrome:
//
//   ┌────────────────────────────────────────────────────────┐
//   │  TopBar   (Chat / Cowork / Code · Email / Calendar · ⌘K)│
//   ├─────────────┬──────────────────────────────────────────┤
//   │ AgentMesh   │  SurfaceRow                              │
//   │ (left rail) ├──────────────────────────────────────────┤
//   │             │  <Route element/>                        │
//   │             │                                          │
//   ├─────────────┴──────────────────────────────────────────┤
//   │  LogDrawer (collapsed by default, ⌘L to expand)        │
//   └────────────────────────────────────────────────────────┘
//
// `focusRole` is App-level state so that clicking a tentacle in the mesh
// sidebar re-scopes the ChangesRenderer on Chat and Cowork. `surface` is
// likewise routed through but currently advisory — the backend will start
// tagging events with `surface` once the engine knows which tool class
// it's using.

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

import TopBar from "./components/TopBar.jsx";
import SurfaceRow from "./components/SurfaceRow.jsx";
import AgentMeshSidebar from "./components/AgentMeshSidebar.jsx";
import LogDrawer from "./components/LogDrawer.jsx";
import CommandPalette from "./components/CommandPalette.jsx";

import ChatV2 from "./pages/ChatV2.jsx";
import CoworkPage from "./pages/CoworkPage.jsx";
import CodePage from "./pages/CodePage.jsx";
import EmailPage from "./pages/EmailPage.jsx";
import CalendarPage from "./pages/CalendarPage.jsx";

// Legacy pages — still reachable under /overflow/* during the V2.2 cutover.
import Agents from "./pages/Agents.jsx";
import Pipeline from "./pages/Pipeline.jsx";
import Projects from "./pages/Projects.jsx";
import Skills from "./pages/Skills.jsx";
import MCPServers from "./pages/MCPServers.jsx";
import Memory from "./pages/Memory.jsx";
import SystemStatus from "./pages/SystemStatus.jsx";

export default function App() {
  return (
    <BrowserRouter>
      <Shell />
    </BrowserRouter>
  );
}

function Shell() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [focusRole, setFocusRole]     = useState(null);
  const [surface, setSurface]         = useState("desktop");

  // ⌘K / Ctrl+K opens the command palette globally.
  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex h-screen flex-col"
         style={{ background: "var(--bg-0)", color: "var(--fg-0)" }}>
      <TopBar onOpenPalette={() => setPaletteOpen(true)} />

      <div className="flex min-h-0 flex-1">
        {/* Left rail — live octopus mesh */}
        <AgentMeshSidebar focus={focusRole} onFocus={setFocusRole} />

        {/* Main column */}
        <main className="flex min-h-0 flex-1 flex-col">
          <SurfaceRow active={surface} onChange={setSurface} />

          <div className="min-h-0 flex-1 overflow-hidden">
            <Routes>
              <Route path="/" element={<Navigate to="/chat" replace />} />

              <Route
                path="/chat"
                element={<ChatV2 focusRole={focusRole} onFocusRole={setFocusRole} surface={surface} />}
              />
              <Route
                path="/cowork"
                element={<CoworkPage focusRole={focusRole} onFocusRole={setFocusRole} surface={surface} />}
              />
              <Route path="/code"     element={<CodePage surface={surface} />} />
              <Route path="/email"    element={<EmailPage surface={surface} />} />
              <Route path="/calendar" element={<CalendarPage surface={surface} />} />

              {/* Legacy */}
              <Route path="/overflow/agents"   element={<Agents />} />
              <Route path="/overflow/pipeline" element={<Pipeline />} />
              <Route path="/overflow/projects" element={<Projects />} />
              <Route path="/overflow/skills"   element={<Skills />} />
              <Route path="/overflow/mcp"      element={<MCPServers />} />
              <Route path="/overflow/memory"   element={<Memory />} />
              <Route path="/overflow/system"   element={<SystemStatus />} />

              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </main>
      </div>

      <LogDrawer />

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

function NotFound() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-center">
        <div className="mono caps mb-1" style={{ color: "var(--fg-3)" }}>404</div>
        <div className="text-sm" style={{ color: "var(--fg-1)" }}>No route matches this path.</div>
      </div>
    </div>
  );
}
