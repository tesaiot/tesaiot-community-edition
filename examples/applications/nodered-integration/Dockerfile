# syntax=docker/dockerfile:1.6

ARG NODE_RED_VERSION=3.1.9-18

FROM node:20-alpine AS builder
WORKDIR /workspace

COPY package.json tsconfig.json ./
COPY src ./src

RUN npm install --include=dev \
  && npm run build \
  && npm prune --omit=dev

FROM nodered/node-red:${NODE_RED_VERSION}
USER root

# Copy compiled nodes and runtime dependencies into the Node-RED userDir
COPY --from=builder /workspace/package.json /data/package.json
COPY --from=builder /workspace/package-lock.json /data/package-lock.json
COPY --from=builder /workspace/node_modules /data/node_modules
COPY --from=builder /workspace/dist /data/dist

# Project assets
COPY flows /data/flows
COPY settings.js /data/settings.js
COPY .env.example /data/.env.example

RUN chown -R node-red:node-red /data

USER node-red
EXPOSE 1880

CMD ["npm", "start", "--", "--userDir", "/data"]
