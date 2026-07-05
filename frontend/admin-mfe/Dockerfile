# [STUB logic, REAL MF wiring] "coming soon" placeholder — see docs/deferred_scope.md.
FROM node:20-slim
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3004
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "3004"]
