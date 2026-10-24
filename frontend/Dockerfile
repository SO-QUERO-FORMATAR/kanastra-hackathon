FROM node:24-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --prefer-offline --no-audit --no-fund --fetch-retries=1 --fetch-timeout=30000
COPY index.html vite.config.ts tsconfig.json ./
COPY src ./src
COPY contracts ./contracts
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--port", "5173", "--strictPort"]
