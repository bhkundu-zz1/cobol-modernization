import { federation } from "@module-federation/vite";
import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 3001 },
  plugins: [
    federation({
      name: "upload_mfe",
      filename: "remoteEntry.js",
      exposes: {
        "./UploadApp": "./src/UploadApp.tsx",
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
