# Deployment Guide

## Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.10+ (for local deployment)
- Redis server
- OpenAI API key (optional, for LLM features)

## Environment Variables

Create a `.env` file with the following variables:

```bash
# Required
APP_NAME=nlp-service
APP_ENV=production
LOG_LEVEL=INFO

# OpenAI (optional but recommended)
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Redis (required for production)
REDIS_URL=redis://redis:6379/0

# Database
DATABASE_URL=sqlite:///./data/nlp_service.db

# Features
CACHE_ENABLED=true
PII_REDACTION_ENABLED=true
USE_LLM_FALLBACK=true
METRICS_ENABLED=true

# Tuning
DEFAULT_TIME_MINUTES=10
ACHIEVEMENT_DEFAULT_WEIGHT=10
HEURISTIC_CONFIDENCE_THRESHOLD=0.8
LLM_TIMEOUT_SECONDS=10
```

## Docker Deployment (Recommended)

### 1. Using Docker Compose

```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Clean up (including volumes)
docker-compose down -v
```

The service will be available at `http://localhost:8000`

### 2. Custom Docker Build

```bash
# Build image
docker build -t nlp-service:latest .

# Run with Redis
docker run -d --name redis redis:7-alpine

docker run -d \
  --name nlp-service \
  -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  -e OPENAI_API_KEY=your_key \
  --link redis \
  nlp-service:latest
```

## Local Deployment

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally and run
redis-server
```

### 3. Run Application

```bash
# Development mode (with auto-reload)
uvicorn nlp_service.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn nlp_service.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Production Deployment

### Using systemd (Linux)

1. Create systemd service file `/etc/systemd/system/nlp-service.service`:

```ini
[Unit]
Description=NLP Service
After=network.target redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/nlp-service
Environment="PATH=/opt/nlp-service/venv/bin"
EnvironmentFile=/opt/nlp-service/.env
ExecStart=/opt/nlp-service/venv/bin/uvicorn nlp_service.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start service:

```bash
sudo systemctl enable nlp-service
sudo systemctl start nlp-service
sudo systemctl status nlp-service
```

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout for long-running LLM requests
        proxy_read_timeout 30s;
    }

    location /metrics {
        # Restrict access to metrics
        allow 10.0.0.0/8;
        deny all;
        
        proxy_pass http://localhost:8000/metrics;
    }
}
```

### Using Kubernetes

Example deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nlp-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nlp-service
  template:
    metadata:
      labels:
        app: nlp-service
    spec:
      containers:
      - name: nlp-service
        image: nlp-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: nlp-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: nlp-service
spec:
  selector:
    app: nlp-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring Setup

### Prometheus

1. Add scrape config to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'nlp-service'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

2. Start Prometheus:

```bash
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus
```

### Grafana

1. Start Grafana:

```bash
docker run -d -p 3000:3000 grafana/grafana
```

2. Add Prometheus as data source
3. Import dashboard with these panels:
   - Request rate (nlp_requests_total)
   - Error rate (nlp_requests_failed_total)
   - Latency percentiles (nlp_request_latency_seconds)
   - LLM calls and cost estimation
   - Cache hit rate

## Scaling Considerations

### Horizontal Scaling

- Service is stateless and can be scaled horizontally
- Use load balancer (Nginx, HAProxy, or cloud LB)
- Ensure Redis is accessible from all instances

### Database Scaling

- For SQLite: consider migrating to PostgreSQL for multi-instance deployments
- Use connection pooling
- Regular backups of action templates database

### Caching Strategy

- Redis recommended for production
- Configure appropriate TTL (default 7 days)
- Monitor cache hit rates and adjust as needed

### LLM Cost Optimization

- Set `HEURISTIC_CONFIDENCE_THRESHOLD` higher to reduce LLM calls
- Use caching aggressively
- Monitor token usage via metrics
- Consider rate limiting per user if needed

## Security Checklist

- [ ] Change default credentials
- [ ] Use HTTPS in production
- [ ] Implement authentication (API keys/JWT)
- [ ] Restrict `/metrics` endpoint access
- [ ] Store API keys in secrets manager
- [ ] Enable PII redaction
- [ ] Set up log rotation
- [ ] Regular security updates
- [ ] Network firewall rules
- [ ] Database encryption at rest

## Backup and Recovery

### Database Backup

```bash
# SQLite
sqlite3 nlp_service.db .dump > backup.sql

# Restore
sqlite3 nlp_service_new.db < backup.sql
```

### Redis Backup

```bash
# Enable persistence in redis.conf
appendonly yes

# Manual backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/
```

## Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Check metrics
curl http://localhost:8000/metrics | grep nlp_requests_total

# Test analysis
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "text": "Тест"}'
```

## Troubleshooting

### Service won't start

- Check logs: `docker-compose logs nlp-service`
- Verify environment variables
- Ensure Redis is accessible
- Check port 8000 is not in use

### High latency

- Check LLM API response times in metrics
- Monitor Redis connection pool
- Check system resources (CPU, memory)
- Review confidence threshold settings

### Cache issues

- Verify Redis connection
- Check Redis memory usage
- Review TTL settings
- Clear cache if corrupted: `DELETE /api/v1/cache`

### LLM errors

- Verify API key is valid
- Check API quota/limits
- Review timeout settings
- Check network connectivity to OpenAI

## Performance Tuning

- **Workers**: 2-4x CPU cores
- **Worker timeout**: 30-60 seconds
- **Redis max memory**: 1-2GB
- **Cache TTL**: 7 days (adjustable)
- **LLM timeout**: 10 seconds
