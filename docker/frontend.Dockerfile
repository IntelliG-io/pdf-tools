# syntax=docker/dockerfile:1.5
FROM node:20-alpine AS builder

WORKDIR /frontend

# Install dependencies first for better caching
COPY apps/frontend/package.json apps/frontend/package-lock.json ./
RUN npm ci

# Copy application source
COPY apps/frontend ./

# Allow overriding the backend URL when building the image
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.25-alpine

# Remove the default config and replace it with a minimal static file server
RUN rm /etc/nginx/conf.d/default.conf
COPY deploy/nginx/frontend-site.conf /etc/nginx/conf.d/frontend.conf

COPY --from=builder /frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
