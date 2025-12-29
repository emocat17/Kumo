# Stage 1: Base
FROM node:20-alpine AS base

WORKDIR /app

# Install base tools
RUN apk add --no-cache git

# Copy dependency definitions
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Stage 2: Development
FROM base AS dev
EXPOSE 6677
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 3: Builder (for Production)
FROM base AS builder
COPY . .
RUN npm run build

# Stage 4: Production (Nginx)
FROM nginx:alpine AS prod
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
