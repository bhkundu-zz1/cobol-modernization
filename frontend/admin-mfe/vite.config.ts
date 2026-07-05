import { federation } from "@module-federation/vite";
import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 3004 },
  plugins: [
    federation({
      name: "admin_mfe",
      filename: "remoteEntry.js",
      exposes: {
        "./AdminApp": "./src/AdminApp.tsx",
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
