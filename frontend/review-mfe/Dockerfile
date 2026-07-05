# Built with context ./frontend (see docker-compose.yml), not just
# review-mfe/, since package.json depends on "@harness/design-system":
# "file:../design-system" — the sibling package must be in the build context.
FROM node:20-slim
WORKDIR /app/design-system

COPY design-system/package.json ./
RUN npm install
COPY design-system/ ./

WORKDIR /app/review-mfe
COPY review-mfe/package.json review-mfe/package-lock.json* ./
RUN npm install

COPY review-mfe/ ./
# @module-federation/vite 1.1.6 has a known intermittent build-time race
# ("Unexpected early exit... Unfinished hook action(s) on exit: (proxyRemoteEntry)
# load virtual:mf-REMOTE_ENTRY_ID") — reproduced under docker-compose's
# BuildKit build pressure but not when this same build runs standalone with
# more resources available. A retry works around it without masking a real
# build error (a genuine syntax/type error fails the same way on every retry).
RUN npm run build || npm run build || npm run build

EXPOSE 3002
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3002"]
