# Built with context ./frontend (see docker-compose.yml), not just
# codegen-mfe/, since package.json depends on "@harness/design-system":
# "file:../design-system" — the sibling package must be in the build context.
FROM node:20-slim
WORKDIR /app/design-system

COPY design-system/package.json ./
RUN npm install
COPY design-system/ ./

WORKDIR /app/codegen-mfe
COPY codegen-mfe/package.json codegen-mfe/package-lock.json* ./
RUN npm install

COPY codegen-mfe/ ./
# @module-federation/vite 1.1.6 has a known intermittent build-time race
# (see review-mfe/Dockerfile) — reproduced under docker-compose's BuildKit
# build pressure but not standalone. A retry works around it without
# masking a real build error.
RUN npm run build || npm run build || npm run build

EXPOSE 3005
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3005"]
