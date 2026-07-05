# Built with context ./frontend (see docker-compose.yml), not just
# editor-mfe/, since package.json depends on "@harness/design-system":
# "file:../design-system" — the sibling package must be in the build context.
FROM node:20-slim
WORKDIR /app/design-system

COPY design-system/package.json ./
RUN npm install
COPY design-system/ ./

WORKDIR /app/editor-mfe
COPY editor-mfe/package.json editor-mfe/package-lock.json* ./
RUN npm install

COPY editor-mfe/ ./
# Same intermittent @module-federation/vite 1.1.6 build-time race review-mfe
# hit under docker-compose's BuildKit build pressure — a retry works around
# it without masking a real build error.
RUN npm run build || npm run build || npm run build

EXPOSE 3003
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3003"]
