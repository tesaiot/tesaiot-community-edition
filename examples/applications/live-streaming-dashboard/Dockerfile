# ==============================================================================
# TESAIoT Live Streaming Dashboard - Production Dockerfile
# ==============================================================================
# Multi-stage build for optimized production image
# Final image: ~25MB using nginx:alpine
#
# Build: docker build -t tesaiot-streaming-dashboard .
# Run:   docker run -p 8080:80 tesaiot-streaming-dashboard
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

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
