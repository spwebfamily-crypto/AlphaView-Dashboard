FROM node:20-alpine AS build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json /app/
RUN npm ci

COPY frontend /app

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_APP_MODE=PAPER

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_APP_MODE=$VITE_APP_MODE

RUN npm run build

FROM nginx:1.27-alpine

COPY infra/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 5173

CMD ["nginx", "-g", "daemon off;"]
