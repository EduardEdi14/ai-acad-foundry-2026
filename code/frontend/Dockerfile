# Two targets from one file.
#
#   dev   the Vite dev server, hot reload, source bind-mounted by docker compose.
#         Fast to work in, and unsuitable for shipping: it compiles on demand,
#         serves unminified modules and expects the source tree to be present.
#
#   prod  the default. React is compiled to static files and served by nginx,
#         which also proxies the API routes — the job vite.config.js does in
#         development. Around 50 MB instead of 500, with no build tool at runtime.
#
# docker-compose.yml asks for `target: dev`; a registry push takes the default.

# --- shared: dependencies ------------------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /srv
# dependencies first — cached until package.json changes
COPY package.json ./
RUN npm install

# --- dev -----------------------------------------------------------------------
FROM deps AS dev
COPY . .
EXPOSE 7800
CMD ["npm", "run", "dev"]

# --- build ---------------------------------------------------------------------
FROM deps AS build
COPY . .
RUN npm run build                      # → /srv/dist

# --- prod ----------------------------------------------------------------------
FROM nginx:1.27-alpine AS prod
COPY --from=build /srv/dist /usr/share/nginx/html
# nginx:alpine substitutes environment variables into /etc/nginx/templates/*.template
# at startup, so API_URL is an ordinary environment variable: the same image serves
# a backend on your machine, next to it in compose, or across the internet in Azure.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV API_URL=http://api:7799
EXPOSE 7800
