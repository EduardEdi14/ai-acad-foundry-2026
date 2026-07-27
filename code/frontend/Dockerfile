FROM node:20-alpine

WORKDIR /srv

# dependencies first — cached until package.json changes
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 7800

# dev server with hot reload; the source is bind-mounted by docker compose
CMD ["npm", "run", "dev"]
