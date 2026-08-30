# ==============================================================================
# MediGen AI - Production Frontend Docker Container
# Multi-stage / Hardened Static Asset Container with Nginx
# ==============================================================================

# Stage 1: Build static bundle with Node.js
FROM node:20-alpine AS builder

WORKDIR /build

# Copy package files for dependency caching
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit

# Copy source files and configuration
COPY tsconfig.json tsconfig.node.json vite.config.ts index.html ./
COPY src/ ./src/

# Build optimized production bundle
RUN npm run build

# ==============================================================================
# Stage 2: Final Nginx Web Server
# ==============================================================================
FROM nginx:1.27-alpine AS final

# Remove default Nginx welcome page
RUN rm -rf /usr/share/nginx/html/*

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled SPA bundle from builder stage
COPY --from=builder /build/dist /usr/share/nginx/html

# Expose standard HTTP port
EXPOSE 80

# Healthcheck verifying /healthz probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/healthz || exit 1

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
