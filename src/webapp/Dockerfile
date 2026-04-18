FROM node:20-alpine

WORKDIR /app

COPY src/webapp/package.json ./src/webapp/
RUN cd src/webapp && npm install

COPY src/webapp/ ./src/webapp/

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]