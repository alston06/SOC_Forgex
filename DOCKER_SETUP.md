# Docker Compose Setup Guide

## Overview

This Docker Compose configuration orchestrates the complete SOC platform with all interconnected services.

## Services Architecture

### Infrastructure Services (Port Range: 2181-9600)
- **Zookeeper** (port 2181) - Kafka coordination
- **Kafka** (ports 9092, 29092) - Event streaming backbone
- **MongoDB** (port 27017) - Case management & metadata storage
- **Redis** (port 6379) - Rate limiting & caching
- **OpenSearch** (ports 9200, 9600) - Log storage & detection queries

### Application Services (Port Range: 8001-8005)
- **Normalizer Service** (port 8001) - Consumes `raw-activity`, enriches logs, produces `normalized-activity`
- **Agent Trigger Service** (port 8002) - Consumes `detection-events`, triggers CrewAI workflows
- **CrewAI Service** (port 8003) - AI agent orchestration (Incident Commander, Triage, Analyst, Threat Intel)
- **Case Service** (port 8004) - Incident management, webhooks, MongoDB CRUD
- **Detection Service** (port 8005) - Consumes `normalized-activity`, runs detection rules, produces `detection-events`

### Frontend Services
- **SOC Dashboard** (port 8501) - Streamlit web UI for analysts
- **User Service** (port 8080) - Mock service for user role enrichment (httpbin)

## Service Interconnections

### Data Flow
```
SDK (Customer Apps)
  ↓ (HTTP POST /v1/logs)
[Future: Ingestion API] 
  ↓ Kafka: raw-activity
Normalizer Service (port 8001)
  ↓ Kafka: normalized-activity
Detection Service (port 8005)
  ↓ Kafka: detection-events
Agent Trigger Service (port 8002)
  ↓ HTTP: POST /kickoff
CrewAI Service (port 8003)
  ↓ HTTP: /internal/case-action, /internal/agent-output
Case Service (port 8004)
  ↓ MongoDB: incidents, notifications
```

### Internal API Dependencies
- **CrewAI** → Normalizer (`/internal/query-logs`), Case Service (`/internal/case-action`, `/internal/agent-output`)
- **Case Service** → Detection Service (`/v1/alerts`), Normalizer (`/internal/query-logs`)
- **Dashboard** → Case Service (`/v1/incidents/*`), Detection Service (`/v1/alerts`)

## Prerequisites

1. **Docker** (v20.10+) and **Docker Compose** (v2.0+)
2. **Environment Variables**:
   - `OPENROUTER_API_KEY` - Required for CrewAI/LLM operations
3. **Network**: Ensure ports 8001-8005, 8080, 8501, 9092, 9200, 27017, 6379 are available

## Quick Start

### 1. Set Environment Variables
```bash
# Create .env file in project root
echo "OPENROUTER_API_KEY=your-api-key-here" > .env
```

### 2. Start All Services
```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f detection-service
```

### 3. Health Checks
```bash
# Check all services are running
docker-compose ps

# Test MongoDB
curl http://localhost:27017

# Test OpenSearch
curl http://localhost:9200

# Test Normalizer API
curl http://localhost:8001/health

# Test Detection API  
curl http://localhost:8005/v1/alerts?tenant_id=tenant-demo-001&limit=10

# Test Case Service
curl http://localhost:8004/v1/incidents?status=OPEN

# Test Dashboard
open http://localhost:8501
```

### 4. Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: deletes all data)
docker-compose down -v
```

## Sample API Key for Testing

A demo API key is pre-configured in MongoDB:
- **API Key**: `test-api-key-123`
- **Tenant ID**: `tenant-demo-001`
- **Usage**: Pass as `X-API-Key` header to ingestion/public endpoints

## Service-Specific Configuration

### Normalizer Service
- **Kafka Topics**: Consumes `raw-activity` → Produces `normalized-activity`
- **OpenSearch**: Writes to `logs-{tenant_id}-{YYYY-MM}` indices
- **GeoIP**: MaxMind GeoLite2-City database at `./normalizer-service/data/GeoLite2-City.mmdb`

### Detection Service
- **Kafka Topics**: Consumes `normalized-activity` → Produces `detection-events`
- **OpenSearch**: Reads from `logs-*`, writes to `detections-{tenant_id}-{YYYY-MM}`
- **Rules**: Brute force, unusual geo, admin abuse, data exfil, error storm

### Case Service
- **MongoDB Collections**: `incidents`, `notifications`, `tenant_webhooks`, `api_keys`, `ingestion_metrics`
- **Internal Auth**: Bearer token `soc-internal-token-v1`

### CrewAI Service
- **LLM Provider**: OpenRouter (OpenAI GPT-4)
- **Agents**: Orchestrator, Triage Analyst, Incident Analyst, Threat Intel
- **Tools**: LogQueryTool, CaseTool, AgentOutputTool

## Troubleshooting

### Services Won't Start
```bash
# Check Docker daemon
docker info

# Check port conflicts
netstat -tulnp | grep -E "8001|8002|8003|8004|8005|8501|9092|9200|27017|6379"

# Check logs for specific service
docker-compose logs case-service
```

### Kafka Connection Issues
```bash
# Check Kafka topics
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Create topics manually if needed
docker-compose exec kafka kafka-topics --create --topic raw-activity --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics --create --topic normalized-activity --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
docker-compose exec kafka kafka-topics --create --topic detection-events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```

### MongoDB Connection Issues
```bash
# Access MongoDB shell
docker-compose exec mongo mongosh soc_db

# Verify collections
db.getCollectionNames()

# Check API keys
db.api_keys.find().pretty()
```

### OpenSearch Issues
```bash
# Check cluster health
curl http://localhost:9200/_cluster/health?pretty

# List indices
curl http://localhost:9200/_cat/indices?v

# Check index templates
curl http://localhost:9200/_index_template?pretty
```

## Development Workflow

### Rebuild Single Service
```bash
docker-compose up -d --build detection-service
```

### View Logs in Real-Time
```bash
docker-compose logs -f --tail=100 detection-service normalizer-service
```

### Execute Commands in Container
```bash
# Python shell in case-service
docker-compose exec case-service python

# MongoDB shell
docker-compose exec mongo mongosh soc_db
```

### Restart Services
```bash
# Restart single service
docker-compose restart detection-service

# Restart all
docker-compose restart
```

## Next Steps

1. **Add Ingestion API** - Service for SDK event ingestion (port 8000)
2. **Configure Webhooks** - Set tenant webhook URLs via `/v1/webhooks` endpoint
3. **Load Sample Data** - Send test events through normalizer to populate dashboard
4. **Configure Alerts** - Tune detection rule thresholds in `detection-scoring-engine/detection/rules/`

## Monitoring

### Resource Usage
```bash
# Check container stats
docker stats

# Check disk usage
docker system df
```

### Service Health
All services expose health check endpoints or can be tested:
- Normalizer: `http://localhost:8001/health` (if implemented)
- Detection: `http://localhost:8005/v1/alerts`
- Case: `http://localhost:8004/v1/incidents`
- Dashboard: `http://localhost:8501`

## Security Notes

- **Internal Token**: Change `soc-internal-token-v1` in production
- **MongoDB**: Enable authentication in production
- **OpenSearch**: Enable security plugin in production
- **API Keys**: Hash with SHA256 before storing
- **Webhooks**: Validate HTTPS URLs in production
