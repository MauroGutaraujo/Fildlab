import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { procesarOutbox } from "./db/outbox";
import "./index.css";

// Android no siempre dispara el evento 'online' de forma confiable: el intervalo de
// respaldo asegura que el Outbox igual se procese si hay señal.
window.addEventListener("online", () => void procesarOutbox());
setInterval(() => {
  if (navigator.onLine) void procesarOutbox();
}, 30_000);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
