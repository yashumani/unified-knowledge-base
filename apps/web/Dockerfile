FROM node:22-slim

WORKDIR /app

COPY package.json ./package.json
COPY packages/create-ukb-brain/package.json ./packages/create-ukb-brain/package.json
COPY apps/web/package.json ./apps/web/package.json

RUN npm install

COPY apps/web ./apps/web

WORKDIR /app/apps/web

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
