FROM node:20-alpine AS builder

WORKDIR /app
COPY src/webapp/package.json ./
RUN npm install
COPY src/webapp/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY src/webapp/nginx.conf /etc/nginx/conf.d/default.conf
