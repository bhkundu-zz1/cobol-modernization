import { federation } from "@module-federation/vite";
import { defineConfig } from "vite";

export default defineConfig({
  // Same fix as review-mfe's vite.config.ts: @harness/design-system ships
  // raw, uncompiled .tsx, and Vite/esbuild's automatic-JSX-runtime default
  // doesn't reliably apply to node_modules-sourced source the way it does
  // for this project's own src/ — forcing it explicitly avoids a "React is
  // not defined" crash at runtime.
  esbuild: {
    jsx: "automatic",
  },
  server: { port: 3005 },
  plugins: [
    federation({
      name: "codegen_mfe",
      filename: "remoteEntry.js",
      exposes: {
        "./CodegenApp": "./src/CodegenApp.tsx",
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
