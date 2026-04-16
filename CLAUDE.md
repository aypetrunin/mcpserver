# mcpserver — MCP Tools Server

## What This Service Does

FastMCP-based tools server. Provides tools for the LangGraph agent to interact with external systems: CRM API, Qdrant vector search, PostgreSQL database. Each client (salon) has its own tool configuration.

## Project Structure

```
mcpserver/
├── main_v2.py                    # Server entrypoint
├── src/
│   ├── settings.py               # Config
│   ├── runtime.py                # Runtime setup
│   ├── http_retry.py             # HTTP retry logic
│   ├── clients.py                # Client definitions
│   ├── timezone_utils.py         # Timezone helpers
│   ├── server/                   # MCP server setup per client
│   │   ├── server_registry.py    # Server registry
│   │   ├── server_spec_factory.py # Spec factory
│   │   ├── server_common.py      # Shared server logic
│   │   ├── server_types.py       # Server type definitions
│   │   └── tools_*.py            # Per-client tool configs (valentina, anastasia, etc.)
│   ├── tools/                    # Tool implementations
│   │   ├── record_time.py        # Book appointment
│   │   ├── get_client_records.py # Get bookings
│   │   ├── delete_client_record.py
│   │   ├── reschedule_client_record.py
│   │   ├── get_client_lessons.py
│   │   ├── get_client_statistics.py
│   │   ├── update_client_info.py
│   │   ├── update_client_lesson.py
│   │   ├── call_administrator.py
│   │   ├── faq.py                # FAQ search (Qdrant)
│   │   ├── services.py           # Services search (Qdrant)
│   │   ├── recommendations.py    # Product recommendations
│   │   ├── class_product_search_*.py  # Product search
│   │   ├── class_avaliable_time_for_master*.py  # Master availability
│   │   ├── remember_*.py         # Context memory tools
│   │   └── lesson_id.py
│   ├── crm/                      # CRM API integration
│   │   ├── _crm_http.py          # CRM HTTP client
│   │   ├── _crm_settings.py      # CRM config
│   │   ├── _crm_result.py        # CRM response types
│   │   └── crm_*.py              # CRM operations
│   ├── postgres/                 # PostgreSQL layer
│   │   ├── db_pool.py            # Connection pool
│   │   ├── postgres_config.py
│   │   ├── postgres_util.py
│   │   └── postgres_create_view.py
│   ├── qdrant/                   # Qdrant vector search
│   │   ├── collections.py
│   │   ├── retriever_common.py
│   │   ├── retriever_faq_services.py
│   │   └── retriever_product.py
│   └── request/
│       └── httpservice_call_administrator.py
├── test/                         # Tests
```

## Common Commands

```bash
# Install deps
uv sync

# Lint & format
uv run ruff check src/
uv run ruff format src/
uv run mypy src/

# Run tests
uv run pytest test/
```

## Code Style

- ruff (line-length=88), mypy strict with pydantic plugin
- pep257-style docstrings
- No prints (T201 rule)
- isort: combine-as-imports, force-sort-within-sections
