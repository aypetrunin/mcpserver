FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip
RUN pip install .

# Пробросить порты можно через EXPOSE (опционально)
EXPOSE 4011

CMD ["python", "main.py"]
