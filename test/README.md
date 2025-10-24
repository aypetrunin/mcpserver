# Запуск теста
pytest

# Запуск теста с сохранением результата
pytest mcp/tests | tee mcp/tests/report.txt

# Запуск теста с сохранением результата
pytest --junit-xml=mcp/tests/report.xml