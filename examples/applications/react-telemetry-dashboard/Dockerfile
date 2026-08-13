# ==============================================================================
# TESAIoT React Dashboard - Docker Build
# ==============================================================================
# Multi-stage build for optimized production image
#
# Stage 1: Build the React application
# Stage 2: Serve with nginx
# ==============================================================================

# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production=false

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Production
FROM nginx:alpine

# Copy custom nginx config
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

# Add healthcheck (nc is always present in the alpine BusyBox; wget is not)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD nc -z 127.0.0.1 8080 || exit 1

# Unprivileged port — see nginx.conf
EXPOSE 8080

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
