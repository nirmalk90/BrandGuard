FROM node:24-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts index.html ./
COPY frontend/ ./frontend/
COPY public/ ./public/
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock \
    && useradd --create-home brandguard \
    && mkdir /data \
    && chown brandguard:brandguard /data
COPY backend/ ./backend/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY --from=frontend /app/dist/ ./dist/
USER brandguard
ENV DATABASE_URL=sqlite:////data/brandguard.sqlite
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn backend.main:app --host 0.0.0.0 --port \"$PORT\""]
