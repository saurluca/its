# Build Stage 1

FROM node:22-alpine AS build
WORKDIR /app

RUN corepack enable

# Copy package.json and your lockfile, here we add pnpm-lock.yaml for illustration
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm i

# Copy the entire project
COPY . ./

# Build the project
RUN pnpm run build

# Build Stage 2

FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Copy the static files from the build stage
COPY --from=build /app/.output/public/ ./

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
