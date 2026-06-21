# Copyright TESAIoT Platform contributors
# SPDX-License-Identifier: Apache-2.0
#
# Production Dockerfile for the TESAIoT Community Edition Admin UI
# Multi-stage build - builds React app inside Docker (no local build needed!)

# Stage 1: Build the React application
FROM node:20-alpine AS builder

# Install git for proper version detection
RUN apk add --no-cache git

# Set working directory
WORKDIR /app

# Set Node.js memory options to prevent SIGBUS errors on the large bundle
ENV NODE_OPTIONS="--max-old-space-size=4096"
ENV NODE_ENV=production

# Copy package manifest + lockfile first for better caching.
# These layers stay cached as long as package.json/package-lock.json are unchanged.
COPY package.json package-lock.json ./

RUN npm install -g npm@11.17.0
RUN npm install --include=dev --no-audit --no-fund

# ============================================================================
# CACHE BOUNDARY: ARG declarations AFTER yarn install
# Build arguments declared here so yarn install layer remains cacheable
# When CACHEBUST changes, only layers AFTER this point are rebuilt
# ============================================================================
ARG CACHEBUST=1
ARG BUILD_DATE=unknown

# Force cache invalidation BEFORE copying source files
# This ensures source changes trigger rebuild
RUN echo "Build date: ${BUILD_DATE}, Cache bust: ${CACHEBUST}" > /tmp/build.info

# Copy all source files AFTER cache bust
COPY . .

# Clean any existing build artifacts before building
RUN rm -rf dist node_modules/.vite node_modules/.cache

# Build with memory optimization to prevent SIGBUS errors
# Using split approach with memory constraints
RUN npm run prebuild

# Run the build with memory constraints - bypass package.json script and run directly
RUN NODE_OPTIONS="--max-old-space-size=4096" npx tsc && \
    NODE_OPTIONS="--max-old-space-size=4096" npx vite build

# Verify build succeeded
RUN test -f dist/index.html || (echo "Build failed!" && exit 1)

# Stage 2: Serve with nginx (pinned to the same version as the platform edge
# nginx in docker-compose.yml)
FROM nginx:1.27.5-alpine3.21

# Build arguments for build info + image labels
ARG CACHEBUST=1
ARG BUILD_DATE=unknown
ARG BUILD_HASH=unknown

# Copy custom nginx config with no-cache settings (not nginx-health.conf which has 1yr cache!)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy public assets from builder
COPY --from=builder /app/public/images /usr/share/nginx/html/images

# Skip deployment manifest copy - files don't exist yet

# Create build info file
RUN echo "BUILD_TIME: ${BUILD_DATE}" > /usr/share/nginx/html/BUILD_INFO && \
    echo "BUILD_ID: ${CACHEBUST}" >> /usr/share/nginx/html/BUILD_INFO && \
    echo "GIT_HASH: ${BUILD_HASH}" >> /usr/share/nginx/html/BUILD_INFO && \
    echo "NGINX_VERSION: $(nginx -v 2>&1)" >> /usr/share/nginx/html/BUILD_INFO

LABEL org.opencontainers.image.title="tesaiot-community-edition-admin-ui" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${BUILD_HASH}" \
      org.opencontainers.image.licenses="Apache-2.0"

# Expose the unprivileged port the server block listens on (see nginx.conf).
# A non-root process cannot bind ports < 1024, so the container serves on 8080.
EXPOSE 8080

# Create non-root user and make every path nginx must write to (pid, cache,
# temp, logs) owned by / writable for it. nginx.conf listens on 8080 so no
# privileged-port bind is needed. Logs are symlinked to stdout/stderr by the
# base image; we also point them there so a read-only/non-root fs is fine.
RUN adduser -D -s /bin/sh -u 1001 nginxuser && \
    mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp /var/log/nginx && \
    chown -R nginxuser:nginxuser /usr/share/nginx/html /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginxuser:nginxuser /var/run/nginx.pid && \
    chmod 1777 /var/run

# Drop privileges: run nginx as the unprivileged nginxuser.
USER nginxuser

# Health check: TCP probe of the unprivileged port via BusyBox nc (the image
# ships no curl/wget guarantees; nc is always present in alpine BusyBox).
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD nc -z 127.0.0.1 8080 || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]