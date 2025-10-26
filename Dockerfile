# Первая стадия: установка зависимостей и сборка
FROM python:3.11-slim AS builder

WORKDIR /app

# Обновление pip и установка uv
RUN pip install --upgrade pip
RUN pip install uv

COPY . .

RUN pip install .
# RUN uv sync

# Вторая стадия: создание финального образа
FROM python:3.11-slim

WORKDIR /app

# Копирование установленных библиотек из builder (зависимости)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Копирование исходного кода из builder, чтобы были последние данные
COPY --from=builder /app /app

EXPOSE 4011
EXPOSE 4012
EXPOSE 4015
EXPOSE 4016
EXPOSE 4017

CMD ["python", "main.py"]



# FROM python:3.11-slim

# WORKDIR /app

# COPY pyproject.toml ./
# COPY src ./src

# RUN pip install --upgrade pip
# RUN pip install .

# # Пробросить порты можно через EXPOSE (опционально)
# # 4011 - Alisa
# # 4012 - Sofia
# EXPOSE 4011
# EXPOSE 4012

# CMD ["python", "main.py"]
