# Build stage
FROM node:22-slim AS build-stage
WORKDIR /app

# Accept build arguments
ARG VITE_API_BASE
ARG VITE_BACKEND_ORIGIN

# Set environment variables for build
ENV VITE_API_BASE=$VITE_API_BASE
ENV VITE_BACKEND_ORIGIN=$VITE_BACKEND_ORIGIN

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:stable-alpine AS production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Custom Nginx config for SPA
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
