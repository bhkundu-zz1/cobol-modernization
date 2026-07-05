import { federation } from "@module-federation/vite";
import { defineConfig } from "vite";

export default defineConfig({
  // Same fix review-mfe needed: @harness/design-system ships raw,
  // uncompiled .tsx, and esbuild's automatic-JSX-runtime default does not
  // reliably apply to node_modules-sourced source. Set explicitly to avoid
  // "React is not defined" the moment this MFE renders Button/Badge.
  esbuild: {
    jsx: "automatic",
  },
  server: { port: 3003 },
  plugins: [
    federation({
      name: "editor_mfe",
      filename: "remoteEntry.js",
      exposes: {
        "./EditorApp": "./src/EditorApp.tsx",
      },
      shared: {
        react: { singleton: true, requiredVersion: "^18.3.0" },
        "react-dom": { singleton: true, requiredVersion: "^18.3.0" },
      },
    }),
  ],
  build: {
    target: "esnext",
    modulePreload: false,
  },
});
