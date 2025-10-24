FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --upgrade pip
RUN pip install .

# Пробросить порты можно через EXPOSE (опционально)
# 4011 - Alisa
# 4012 - Sofia
EXPOSE 4011
EXPOSE 4012

CMD ["python", "main.py"]
