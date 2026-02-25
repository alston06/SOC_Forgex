# Quick Start Guide - SOC Platform Demo

## Prerequisites
- Docker and Docker Compose installed
- `OPENROUTER_API_KEY` in `.env` file

## Start All Services

```bash
# From project root
docker-compose up -d

# Watch logs
docker-compose logs -f
```

## Verify Services Running

```bash
# Check all services are up
docker-compose ps

# Should see all services with "Up" status:
# - zookeeper, kafka, mongo, redis, opensearch (infrastructure)
# - normalizer-service, detection-service, case-service, 
#   crewai-service, agent-trigger-service (application)
# - soc-dashboard, user-service (frontend/mock)
```

## Access the Dashboard

1. Open browser: **http://localhost:8501**
2. In sidebar configuration:
   - **API Key**: `test-api-key-123`
   - **Case Service URL**: `http://localhost:8004`
   - **Detection Service URL**: `http://localhost:8005`

## Generate Sample Data (for Demo)

### Method 1: Using Kafka CLI

```bash
# Create a sample normalized event
docker-compose exec -T kafka kafka-console-producer \
  --topic normalized-activity \
  --bootstrap-server localhost:9092 << EOF
{"tenant_id":"tenant-demo-001","event":{"timestamp":"2026-02-25T10:00:00Z","event_type":"auth_login","actor":"user123","resource":"/auth/login","action":"POST","source":"demo-app","ip":"192.168.1.100","user_agent":"Mozilla/5.0","service_name":"demo-service","normalized_path":"/auth/login","event_id":"evt-001","extras":{"success":false}}}
EOF

# Create multiple failed login attempts (triggers brute force rule)
for i in {1..6}; do
  echo '{"tenant_id":"tenant-demo-001","event":{"timestamp":"2026-02-25T10:0'$i':00Z","event_type":"auth_login","actor":"attacker","resource":"/auth/login","action":"POST","source":"demo-app","ip":"10.0.0.1","user_agent":"curl/7.0","service_name":"demo-service","normalized_path":"/auth/login","event_id":"evt-00'$i'","extras":{"success":false}}}'
done | docker-compose exec -T kafka kafka-console-producer --topic normalized-activity --bootstrap-server localhost:9092
```

### Method 2: Check Existing Data

```bash
# Check for alerts in detection service
curl "http://localhost:8005/v1/alerts?tenant_id=tenant-demo-001&limit=50"

# Check for incidents in case service
curl -H "X-API-Key: test-api-key-123" \
  "http://localhost:8004/v1/incidents?status=OPEN"
```

## Test Individual Services

### Detection Service
```bash
# Get alerts (empty if no detections yet)
curl "http://localhost:8005/v1/alerts?tenant_id=tenant-demo-001&limit=10"
```

### Case Service
```bash
# List open incidents (requires API key)
curl -H "X-API-Key: test-api-key-123" \
  "http://localhost:8004/v1/incidents?status=OPEN"
```

### MongoDB
```bash
# Check collections
docker-compose exec mongo mongosh soc_db --quiet \
  --eval "db.getCollectionNames()"

# Check API keys
docker-compose exec mongo mongosh soc_db --quiet \
  --eval "db.api_keys.find().pretty()"
```

### OpenSearch
```bash
# Check cluster health
curl "http://localhost:9200/_cluster/health?pretty"

# List indices
curl "http://localhost:9200/_cat/indices?v"
```

### Kafka
```bash
# List topics
docker-compose exec kafka kafka-topics \
  --list --bootstrap-server localhost:9092

# Consume from detection-events topic
docker-compose exec kafka kafka-console-consumer \
  --topic detection-events \
  --bootstrap-server localhost:9092 \
  --from-beginning
```

## Trigger AI Agent Workflow

Once you have a detection event, it will automatically:
1. Flow to `detection-events` Kafka topic
2. Trigger Agent Trigger Service
3. Call CrewAI Service `/kickoff`
4. Run 4 AI agents (Orchestrator, Triage, Analyst, Threat Intel)
5. Create incident in Case Service via `/internal/case-action`
6. Store agent outputs via `/internal/agent-output`

Monitor the flow:
```bash
# Watch CrewAI service logs
docker-compose logs -f crewai-service

# Watch case service logs
docker-compose logs -f case-service
```

## Dashboard Features

Once you access http://localhost:8501:

### Overview Tab
- Active incidents count
- Alerts per hour
- MTTA/MTTR metrics
- Severity distribution

### Alerts Tab
- Recent detections
- Filter by severity, confidence
- Click to view details

### Incidents Tab
- List of open/closed incidents
- Status, severity, created time
- "View" button for details

### Incident Detail Tab
- Full incident information
- Agent summaries (Triage, Analyst, Intel)
- Related logs
- Human notes
- Status change buttons

### Hunting Tab
- Query logs by actor, service, path
- Time range selection
- Results in table format

### Settings Tab
- API key management
- Webhook configuration
- Service health status

## Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove all data (CAUTION)
docker-compose down -v
```

## Troubleshooting

### Services won't start
```bash
# Check logs for specific service
docker-compose logs detection-service

# Rebuild specific service
docker-compose up -d --build detection-service
```

### Port conflicts
```bash
# Check what's using port 8501 (dashboard)
sudo netstat -tulnp | grep 8501

# Change port in docker-compose.yml if needed
```

### OpenSearch not healthy
```bash
# Check OpenSearch logs
docker-compose logs opensearch

# May need more memory
# Edit docker-compose.yml: OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g
```

### Dashboard can't connect to services
Make sure you use:
- **localhost:8004** for Case Service (from browser)
- **localhost:8005** for Detection Service (from browser)

Don't use container names from the browser.

## Service Endpoints Reference

| Service | Port | Endpoints |
|---------|------|-----------|
| Dashboard | 8501 | http://localhost:8501 |
| Normalizer | 8001 | /internal/query-logs |
| Agent Trigger | 8002 | - |
| CrewAI | 8003 | /kickoff |
| Case Service | 8004 | /v1/incidents, /v1/webhooks |
| Detection | 8005 | /v1/alerts |
| User Mock | 8080 | /anything (httpbin) |
| OpenSearch | 9200 | /_cluster/health |
| MongoDB | 27017 | - |
| Redis | 6379 | - |
| Kafka | 9092 | - |
| Zookeeper | 2181 | - |

## Demo Flow

1. **Start Services**: `docker-compose up -d`
2. **Verify Running**: `docker-compose ps`
3. **Generate Events**: Use Kafka CLI to inject events
4. **Watch Detection**: `docker-compose logs -f detection-service`
5. **See Alerts**: `curl localhost:8005/v1/alerts?tenant_id=tenant-demo-001&limit=10`
6. **Trigger Agents**: Detection events auto-trigger CrewAI
7. **View Dashboard**: Open http://localhost:8501
8. **Check Incidents**: Navigate to Incidents tab in dashboard

## Support

- See [DOCKER_SETUP.md](./DOCKER_SETUP.md) for detailed configuration
- See [SERVICE_STATUS.md](./SERVICE_STATUS.md) for architecture and status
- Check service logs: `docker-compose logs -f <service-name>`
