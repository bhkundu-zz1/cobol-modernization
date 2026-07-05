import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import EditorApp from "./EditorApp";

const container = document.getElementById("root");
if (!container) {
  throw new Error("root element not found");
}

createRoot(container).render(
  <StrictMode>
    <EditorApp />
  </StrictMode>
);
