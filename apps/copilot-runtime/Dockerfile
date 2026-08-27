FROM node:22-alpine AS build
WORKDIR /app

COPY package.json ./
COPY apps/copilot-runtime/package.json apps/copilot-runtime/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/create-ukb-brain/package.json packages/create-ukb-brain/package.json
RUN npm install --no-audit --no-fund

COPY apps/copilot-runtime apps/copilot-runtime
RUN npm --workspace apps/copilot-runtime run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY package.json ./
COPY apps/copilot-runtime/package.json apps/copilot-runtime/package.json
COPY apps/web/package.json apps/web/package.json
COPY packages/create-ukb-brain/package.json packages/create-ukb-brain/package.json
RUN npm install --omit=dev --no-audit --no-fund
COPY --from=build /app/apps/copilot-runtime/dist apps/copilot-runtime/dist

USER node
EXPOSE 8200
CMD ["node", "apps/copilot-runtime/dist/server.js"]
