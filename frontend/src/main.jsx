import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.jsx";
import { ZoneProvider } from "./hooks/useZone.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <ZoneProvider>
      <App />
    </ZoneProvider>
  </StrictMode>
);
