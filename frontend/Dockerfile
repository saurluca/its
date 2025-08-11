# Build Stage 1
FROM node:22-alpine AS build
WORKDIR /app

ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}
ENV NUXT_SESSION_PASSWORD=${NUXT_SESSION_PASSWORD}

RUN corepack enable

# Copy package.json and your lockfile, here we add pnpm-lock.yaml for illustration
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN pnpm i

# Copy the entire project
COPY . ./

# Prepare Nuxt (generates .nuxt directory and type definitions)
RUN pnpm run postinstall

# Build the project
RUN pnpm run build

# Build Stage 2

FROM caddy:2-alpine
WORKDIR /srv

# Copy the static files from the build stage
COPY --from=build /app/.output/public/ ./

# Copy Caddyfile configuration
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80
EXPOSE 443

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
