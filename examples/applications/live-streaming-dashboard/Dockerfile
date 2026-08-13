# ==============================================================================
# TESAIoT Live Streaming Dashboard - Production Dockerfile
# ==============================================================================
# Multi-stage build for optimized production image
# Final image: ~25MB using nginx:alpine
#
# Build: docker build -t tesaiot-streaming-dashboard .
# Run:   docker run -p 8080:8080 tesaiot-streaming-dashboard
# ==============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files first (for better layer caching)
COPY package.json package-lock.json* ./

# Install dependencies
# Use --frozen-lockfile for reproducible builds
RUN npm ci --frozen-lockfile 2>/dev/null || npm install

# Copy source files
COPY . .

# Build the application
# Outputs to /app/dist
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Production
# -----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Labels for container identification
LABEL org.opencontainers.image.title="TESAIoT Live Streaming Dashboard"
LABEL org.opencontainers.image.description="Real-time MQTT telemetry visualization"
LABEL org.opencontainers.image.source="https://github.com/tesaiot/developer-hub"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Run as a non-root user. The stock nginx image runs as root, which this example
# would otherwise teach by default — and an example is where people copy from.
# A non-root process cannot bind ports below 1024, so nginx.conf listens on 8080
# and every path nginx writes to (pid, caches, logs) is made writable for it.
# Mirrors the same treatment in services/admin-ui/Dockerfile.
RUN adduser -D -s /bin/sh -u 1001 nginxuser && \
    mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp /var/log/nginx && \
    chown -R nginxuser:nginxuser /usr/share/nginx/html /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginxuser:nginxuser /var/run/nginx.pid && \
    chmod 1777 /var/run

USER nginxuser

# Unprivileged port — see nginx.conf
EXPOSE 8080

# Health check (nc is always present in the alpine BusyBox; wget is not)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD nc -z 127.0.0.1 8080 || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
