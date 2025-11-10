# Examples

This directory contains examples and test datasets for the NLP service.

## Files

- **`example_requests.py`**: Python script demonstrating various API calls
- **`sample_dataset.txt`**: Sample diary entries with expected outputs

## Running Examples

### Prerequisites

Make sure the service is running:

```bash
# Using Docker
docker-compose up

# Or locally
uvicorn nlp_service.api.main:app --reload
```

### Python Examples

```bash
# Install httpx if not already installed
pip install httpx

# Run examples
python examples/example_requests.py
```

### cURL Examples

#### Health Check

```bash
curl http://localhost:8000/health
```

#### Analyze Text

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 12345,
    "text": "Сходил в зал, потренировался 90 минут",
    "date": "2025-11-10"
  }'
```

#### Get User Stats

```bash
curl http://localhost:8000/api/v1/stats/12345
```

#### Get Metrics

```bash
curl http://localhost:8000/metrics
```

## Test Dataset

The `sample_dataset.txt` file contains example diary entries with expected outputs. You can use this to:

1. Test the service manually
2. Create automated tests
3. Evaluate model performance
4. Train custom models

## Adding More Examples

To add more examples:

1. Add entries to `sample_dataset.txt`
2. Update `example_requests.py` with new test cases
3. Document expected behavior

## Creating JSONL Dataset

For machine learning evaluation, convert the sample dataset to JSONL format:

```python
import json

examples = []

# Read sample_dataset.txt and convert to JSONL
# (Add your conversion logic here)

with open('test_dataset.jsonl', 'w', encoding='utf-8') as f:
    for example in examples:
        f.write(json.dumps(example, ensure_ascii=False) + '\n')
```

## Performance Testing

For load testing:

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Run load test
hey -n 1000 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "text": "Сходил в зал"}' \
  http://localhost:8000/api/v1/analyze
```
