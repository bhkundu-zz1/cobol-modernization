import { federation } from "@module-federation/vite";
import { defineConfig } from "vite";

// Remote URLs come from the environment (never hardcoded), per this
// project's .env-everywhere rule and architecture.md section 8. Vite
// exposes build-time env vars prefixed VITE_ via import.meta.env; these are
// read here (config-time) rather than at runtime since Module Federation's
// `remotes` map must be known at build/dev-server start.
//
// The local-dev fallback (no env var set) points at each remote's Vite dev
// server root, e.g. http://localhost:3001/remoteEntry.js — NOT
// /assets/remoteEntry.js, which is only where the *built* (docker-compose,
// `vite build` + static serve) output lives. `.env`'s SHELL_REMOTE_*_URL
// values use the /assets/ path since docker-compose serves built dist/
// output; this fallback exists for `npm run dev` without docker-compose.
const remoteUrl = (envVar: string, fallbackPort: number) =>
  process.env[envVar] || `http://localhost:${fallbackPort}/remoteEntry.js`;

export default defineConfig({
  server: { port: 3000 },
  plugins: [
    federation({
      name: "shell",
      remotes: {
        upload_mfe: { type: "module", name: "upload_mfe", entry: remoteUrl("VITE_SHELL_REMOTE_UPLOAD_URL", 3001) },
        review_mfe: { type: "module", name: "review_mfe", entry: remoteUrl("VITE_SHELL_REMOTE_REVIEW_URL", 3002) },
        editor_mfe: { type: "module", name: "editor_mfe", entry: remoteUrl("VITE_SHELL_REMOTE_EDITOR_URL", 3003) },
        admin_mfe: { type: "module", name: "admin_mfe", entry: remoteUrl("VITE_SHELL_REMOTE_ADMIN_URL", 3004) },
        codegen_mfe: { type: "module", name: "codegen_mfe", entry: remoteUrl("VITE_SHELL_REMOTE_CODEGEN_URL", 3005) },
      },
      shared: {
        react: { singleton: true, requiredVersion: "^18.3.0" },
        "react-dom": { singleton: true, requiredVersion: "^18.3.0" },
      },
    }),
  ],
  build: {
    target: "esnext",
  },
});
