import { federation } from "@module-federation/vite";
import { defineConfig } from "vite";

export default defineConfig({
  // @harness/design-system ships raw, uncompiled .tsx (its package.json
  // "main" points straight at src/index.tsx — see frontend/design-system's
  // README). Vite/esbuild's automatic-JSX-runtime default does not
  // reliably apply to node_modules-sourced source the way it does inside
  // this project's own src/ — confirmed as a live bug: design-system's
  // components compiled down to classic-runtime `React.createElement(...)`
  // calls with no `React` import, crashing at runtime with "React is not
  // defined" the moment the Review MFE rendered inside the shell. Setting
  // this explicitly forces the automatic runtime for every file esbuild
  // transforms in this build, regardless of source location.
  esbuild: {
    jsx: "automatic",
  },
  server: { port: 3002 },
  plugins: [
    federation({
      name: "review_mfe",
      filename: "remoteEntry.js",
      exposes: {
        "./ReviewApp": "./src/ReviewApp.tsx",
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
