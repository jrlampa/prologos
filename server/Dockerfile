FROM node:20-bullseye-slim AS frontend
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM node:20-bullseye-slim AS api
WORKDIR /app/server

COPY server/package.json ./
RUN npm install --omit=dev

COPY server/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

CMD ["npm", "start"]

