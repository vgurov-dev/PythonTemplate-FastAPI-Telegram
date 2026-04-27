FROM node:20-alpine

# Create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY --chown=appuser:appgroup src/webapp/package.json ./src/webapp/
RUN cd src/webapp && npm install

COPY --chown=appuser:appgroup src/webapp/ ./src/webapp/

USER appuser
EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
