# Project Structure

```
nlp_service/
├── src/
│   └── nlp_service/
│       ├── __init__.py
│       ├── api/                      # FastAPI application
│       │   ├── __init__.py
│       │   ├── main.py              # Entry point, routes
│       │   ├── dependencies.py      # DI container
│       │   ├── schemas.py           # Request/response schemas
│       │   ├── logging_config.py    # Structured logging
│       │   └── metrics.py           # Prometheus metrics
│       ├── core/                     # Core business logic
│       │   ├── __init__.py
│       │   └── analyzer.py          # Main orchestrator
│       ├── domain/                   # Domain models
│       │   ├── __init__.py
│       │   └── models.py            # Pydantic models
│       ├── interfaces/               # Service interfaces
│       │   ├── __init__.py
│       │   └── protocols.py         # Protocol definitions
│       ├── services/                 # Service implementations
│       │   ├── __init__.py
│       │   ├── preprocessor.py      # Text preprocessing, PII
│       │   ├── heuristic_parser.py  # Keyword-based parsing
│       │   ├── llm_parser.py        # LLM integration
│       │   ├── history_service.py   # Action history
│       │   ├── cache_service.py     # Caching layer
│       │   ├── fusion_service.py    # Result fusion
│       │   └── postprocessor.py     # Normalization, dedup
│       └── config/                   # Configuration
│           ├── __init__.py
│           └── settings.py          # Pydantic settings
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── test_preprocessor.py
│   ├── test_heuristic_parser.py
│   ├── test_history_service.py
│   ├── test_cache_service.py
│   ├── test_fusion_service.py
│   ├── test_postprocessor.py
│   ├── test_integration.py          # Integration tests
│   └── test_api.py                  # API tests
├── docs/                             # Documentation
│   ├── API_CONTRACT.md              # API documentation
│   └── DEPLOYMENT.md                # Deployment guide
├── examples/                         # Usage examples
│   ├── README.md
│   ├── example_requests.py          # Python examples
│   └── sample_dataset.txt           # Test data
├── .github/
│   └── workflows/
│       └── ci.yml                   # GitHub Actions CI
├── .env.example                      # Environment template
├── .gitignore
├── .flake8                          # Flake8 config
├── Dockerfile                        # Docker image
├── docker-compose.yml               # Docker Compose config
├── Makefile                         # Build commands
├── pyproject.toml                   # Poetry config
├── requirements.txt                 # Dependencies
├── README.md                        # Main documentation
├── QUICKSTART.md                    # Quick start guide
└── PROJECT_STRUCTURE.md             # This file
```

## Module Responsibilities

### API Layer (`api/`)
- HTTP request handling
- Request validation
- Response serialization
- Dependency injection setup
- Logging and metrics collection

### Core Layer (`core/`)
- **Analyzer**: Orchestrates the entire analysis pipeline
- Coordinates all services
- Manages caching and history recording

### Domain Layer (`domain/`)
- Data models and business entities
- Type definitions
- Validation rules
- No business logic

### Interfaces Layer (`interfaces/`)
- Protocol definitions for DI
- Abstract base classes
- Service contracts

### Services Layer (`services/`)
Each service has a single responsibility:

- **Preprocessor**: Text cleaning, PII redaction, normalization
- **HeuristicParser**: Fast keyword/regex-based parsing
- **LLMParser**: OpenAI API integration with retry logic
- **HistoryService**: Stores and retrieves action templates
- **CacheService**: Redis/memory caching
- **FusionService**: Merges heuristic + LLM results, time estimation
- **Postprocessor**: Deduplication, validation, normalization

### Configuration Layer (`config/`)
- Environment-based settings
- Pydantic validation
- Default values

## Data Flow

```
Request
  ↓
FastAPI (main.py)
  ↓
TextAnalyzer (analyzer.py)
  ↓
├─→ Preprocessor → Clean text
│     ↓
├─→ HeuristicParser → Quick parse
│     ↓
├─→ LLMParser (if needed) → Deep parse
│     ↓
├─→ FusionService → Merge + time estimation
│     ↓
├─→ Postprocessor → Normalize + deduplicate
│     ↓
└─→ HistoryService → Record for future
  ↓
Response (JSON)
```

## Key Design Patterns

- **Dependency Injection**: Clean separation of concerns
- **Protocol-based Programming**: Flexible service contracts
- **Strategy Pattern**: Multiple parsers (heuristic, LLM)
- **Facade Pattern**: TextAnalyzer hides complexity
- **Repository Pattern**: History and cache services
- **Pipeline Pattern**: Sequential processing stages

## Testing Strategy

- **Unit tests**: Each service in isolation
- **Integration tests**: Full pipeline end-to-end
- **API tests**: HTTP endpoint behavior
- **Fixtures**: Shared test data and mocks
- **Coverage target**: ≥80%

## Extension Points

To extend the service:

1. **Add new parser**: Implement `Parser` protocol
2. **Add new category**: Update `heuristic_parser._build_category_keywords()`
3. **Add new LLM provider**: Implement `LLMParser` protocol
4. **Add new storage**: Implement `HistoryLookupService` protocol
5. **Add new cache backend**: Implement `CacheService` protocol

## Dependencies

### Production
- **fastapi**: Web framework
- **pydantic**: Data validation
- **openai**: LLM integration
- **redis**: Caching
- **structlog**: Logging
- **prometheus-client**: Metrics
- **httpx**: HTTP client
- **tenacity**: Retry logic

### Development
- **pytest**: Testing framework
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

## Configuration Management

Settings priority (highest to lowest):
1. Environment variables
2. `.env` file
3. Default values in `settings.py`

## Logging

- JSON structured logs via `structlog`
- No PII in logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request IDs for tracing

## Metrics

Prometheus metrics exported at `/metrics`:
- Request counts and rates
- Latency histograms
- Error rates
- LLM usage and costs
- Cache hit rates

## Security Considerations

- PII redaction in preprocessor
- API keys in environment variables
- No raw text in logs
- Input validation via Pydantic
- Rate limiting support
