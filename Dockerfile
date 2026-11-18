FROM node:24-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY tsconfig.json vite.config.ts index.html ./
COPY frontend/ ./frontend/
COPY public/ ./public/
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr-eng libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt -c requirements.lock \
    && useradd --create-home brandguard \
    && mkdir /data \
    && chown brandguard:brandguard /data
COPY backend/ ./backend/
COPY wordpress/ ./wordpress/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY --from=frontend /app/dist/ ./dist/
USER brandguard
ENV DATABASE_URL=sqlite:////data/brandguard.sqlite
ENV BRANDGUARD_MODE=team TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn backend.main:app --host 0.0.0.0 --port \"$PORT\""]
