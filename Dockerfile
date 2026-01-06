FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости для сборки
RUN apt-get update && apt-get install -y curl && \
    pip install --upgrade pip && \
    pip install uv && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Маркер для определения запуска в контейнере
ENV IS_DOCKER=1

# Копируем проект
COPY . .

# Устанавливаем зависимости через uv
RUN uv sync --frozen --no-dev

# Устанавливаем пакет приложения
RUN uv pip install --no-deps .

# Открываем порт
# EXPOSE 5001 5002 5005 5006 5007 5017 5018 5020

# Запуск
CMD ["uv", "run", "python", "main.py"]