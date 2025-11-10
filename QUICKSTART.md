# Quick Start Guide

Get the NLP service up and running in 5 minutes.

## 1. Clone and Setup

```bash
cd nlp_service

# Copy environment file
cp .env.example .env

# Edit .env and add your OpenAI API key (optional)
# OPENAI_API_KEY=your_key_here
```

## 2. Run with Docker (Recommended)

```bash
# Start all services
docker-compose up

# Service will be available at http://localhost:8000
```

That's it! The service is now running.

## 3. Test the Service

Open another terminal and test:

```bash
# Health check
curl http://localhost:8000/health

# Analyze text
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "text": "Сходил в зал, потренировался 90 минут"
  }'
```

## 4. View API Documentation

Open in browser: http://localhost:8000/docs

Interactive Swagger UI for testing all endpoints.

## Alternative: Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (in separate terminal)
docker run -d -p 6379:6379 redis:7-alpine

# Run service
uvicorn nlp_service.api.main:app --reload
```

## Next Steps

- **Read full documentation**: [README.md](README.md)
- **API reference**: [docs/API_CONTRACT.md](docs/API_CONTRACT.md)
- **Deployment guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Run examples**: `python examples/example_requests.py`
- **Run tests**: `make test`

## Common Issues

**Service won't start?**
- Check if port 8000 is free: `netstat -an | findstr 8000` (Windows) or `lsof -i :8000` (Linux/Mac)
- Check Docker is running: `docker ps`

**Redis connection error?**
- Make sure Redis container is running: `docker ps | grep redis`
- Or disable caching: Set `CACHE_ENABLED=false` in `.env`

**LLM not working?**
- Add `OPENAI_API_KEY` to `.env`
- Or use heuristics only: Set `USE_LLM_FALLBACK=false`

## Need Help?

Check the [README.md](README.md) for detailed documentation or open an issue.
