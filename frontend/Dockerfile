# use the official Bun image
# see all versions at https://hub.docker.com/r/oven/bun/tags
FROM oven/bun:1 AS build
WORKDIR /app

# Set environment variables for build-time
ARG NUXT_SESSION_PASSWORD
ARG NUXT_PUBLIC_API_BASE
ENV NUXT_SESSION_PASSWORD=${NUXT_SESSION_PASSWORD}
ENV NUXT_PUBLIC_API_BASE=${NUXT_PUBLIC_API_BASE}

COPY package.json bun.lock ./

# use ignore-scripts to avoid builting node modules like better-sqlite3
RUN bun install --frozen-lockfile --ignore-scripts

# Copy the entire project
COPY . .

RUN bun --bun run build

# copy production dependencies and source code into final image
FROM oven/bun:1 AS production
WORKDIR /app

# Only `.output` folder is needed from the build stage
COPY --from=build /app/.output /app

# run the app
EXPOSE 3000/tcp
ENTRYPOINT [ "bun", "--bun", "run", "/app/server/index.mjs" ]
