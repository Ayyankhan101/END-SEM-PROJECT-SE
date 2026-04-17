# Build stage
FROM node:18-alpine AS builder

# Create non-root user for build
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

WORKDIR /app

# Copy package files
COPY --chown=nextjs:nodejs package.json package-lock.json* ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit && \
    npm cache clean --force

# Copy source files
COPY --chown=nextjs:nodejs . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine AS production

# Create non-root user
RUN addgroup -g 1001 -S nginx && \
    adduser -S nginx -u 1001

# Install security updates
RUN apk update && apk upgrade && rm -rf /var/cache/apk/*

# Copy built application
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# Create required directories with proper permissions
RUN mkdir -p /var/cache/nginx /var/run && \
    chown -R nginx:nginx /var/cache/nginx /var/run /usr/share/nginx/html && \
    chmod -R 755 /usr/share/nginx/html

# Remove default server definition
RUN rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true

# Use custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -q --spider http://localhost:80 || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]