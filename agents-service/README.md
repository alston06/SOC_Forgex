# Agents Service

Agent orchestration system for SOC Forgex with CrewAI triggers and automated incident analysis.

## Architecture

```
detection-events (Kafka)
    “
agent-trigger-service:8002
    “ (POST /kickoff)
crewai-service:8003
    “ (background flow)
1. Open case ’ case-service:8004
2. Triage (30min logs) ’ normalizer-service:8001
3. Update case (if severity upgrade) ’ case-service:8004
4. Deep analysis (24h logs) ’ normalizer-service:8001
5. Threat intel ’ case-service:8004
6. Finalize ’ case-service:8004
```

## Quick Start

### With Docker (recommended)

```bash
# Set your OpenRouter API key
export OPENROUTER_API_KEY="your-openrouter-api-key"

# Start all services
cd /home/aryaniyaps/web-projects/SOC_Forgex
docker-compose up --build
```

### Local Development

#### 1. Start case-service
```bash
cd /home/aryaniyaps/web-projects/SOC_Forgex/case-service
uv sync
uv run python -m case
```

#### 2. Start crewai-service
```bash
cd /home/aryaniyaps/web-projects/SOC_Forgex/agents-service
uv sync
uv run python crewai.py
```

#### 3. Start trigger-service
```bash
cd /home/aryaniyaps/web-projects/SOC_Forgex/agents-service
uv run python trigger.py
```

## Configuration

### OpenRouter Setup

1. Get your API key from https://openrouter.ai/keys
2. Set environment variable:
   ```bash
   export OPENROUTER_API_KEY="your-api-key"
   ```
3. Configure the model to use (see https://openrouter.ai/models for available models):
   ```bash
   export CREWAI_LLM_MODEL="openai/gpt-4"  # or "anthropic/claude-3-opus", etc.
   ```

### Environment Variables

Create a `.env` file in the agents-service root:

```bash
# Agent Trigger Service
TRIGGER_SERVICE_NAME=agent-trigger-service
TRIGGER_KAFKA_BOOTSTRAP_SERVERS=kafka:9092
TRIGGER_KAFKA_INPUT_TOPIC=detection-events
TRIGGER_KAFKA_GROUP_ID=agent-trigger-v1
TRIGGER_CREWAI_SERVICE_URL=http://crewai-service:8003

# CrewAI Service
CREWAI_LLM_PROVIDER=openrouter  # or "openai"
CREWAI_LLM_API_KEY=your-openrouter-api-key
CREWAI_LLM_MODEL=openai/gpt-4
CREWAI_LLM_TEMPERATURE=0.1

# Caching (saves money!)
CREWAI_LLM_CACHE_ENABLED=true
CREWAI_LLM_CACHE_TTL_SECONDS=3600  # Cache for 1 hour

# Internal Services
CREWAI_NORMALIZER_SERVICE_URL=http://normalizer-service:8001
CREWAI_CASE_SERVICE_URL=http://case-service:8004
```

## Testing

### Test case-service

```bash
# Health check
curl http://localhost:8004/health

# Create a test case
curl -X POST http://localhost:8004/internal/case-action \
  -H "Authorization: Bearer soc-internal-token-v1" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "open",
    "tenant_id": "tenant-123",
    "detection_id": "det-001",
    "severity": "HIGH",
    "summary": "Test case"
  }'
```

### Test crewai-service

```bash
# Health check
curl http://localhost:8003/health

# Service info
curl http://localhost:8003/

# Check cache stats
curl http://localhost:8003/cache/stats

# Trigger analysis (requires case-service running)
curl -X POST http://localhost:8003/kickoff \
  -H "Authorization: Bearer soc-internal-token-v1" \
  -H "Content-Type: application/json" \
  -d '{
    "detection": {
      "detection_id": "det-001",
      "tenant_id": "tenant-123",
      "timestamp": "2026-02-25T10:00:00Z",
      "triggered_events": ["login_failure"],
      "rule_id": "rule-001",
      "severity": "HIGH",
      "confidence": 0.9,
      "description": "Multiple failed logins",
      "entities": {"actor": ["user123"], "ip": ["10.0.0.1"]},
      "evidence": {"attempts": 5}
    }
  }'
```

### Full Integration Test

1. Start all services (case, crewai, trigger, normalizer, kafka)
2. Publish a detection event to Kafka:
   ```bash
   # Requires kafka-console-producer or similar tool
   echo '{"detection_id":"det-002",...}' | kafka-console-producer \
     --broker-list localhost:9092 \
     --topic detection-events
   ```
3. Monitor logs and check:
   - Case created in case-service logs
   - Cache hit rate in `/cache/stats`

## API Endpoints

### case-service:8004
- `GET /health` - Health check
- `POST /internal/case-action` - Open/update/close cases
- `POST /internal/agent-output` - Store agent outputs

### crewai-service:8003
- `GET /` - Service info
- `GET /health` - Health check
- `GET /cache/stats` - LLM cache statistics
- `POST /cache/clear` - Clear cache
- `POST /kickoff` - Start analysis flow (internal auth required)

### agent-trigger-service:8002
- `GET /healthz` - Health check (for probes)

## Cost Optimization

The LLM caching automatically saves money by:
1. **Hashing prompts** with model and temperature
2. **Storing responses** in memory with TTL
3. **Reusing responses** for identical requests

Monitor cache efficiency:
```bash
curl http://localhost:8003/cache/stats
```

Response:
```json
{
  "cache_hits": 42,
  "cache_misses": 15,
  "hit_rate_percent": 73.68,
  "cache_entries": 42
}
```

### Recommended OpenRouter Models (cost-effective)

- `openai/gpt-4o-mini` - Fast, cheap, good for triage
- `anthropic/claude-3-haiku` - Very fast, good for simple tasks
- `openai/gpt-4o` - Balanced performance/cost
- `anthropic/claude-3-opus` - Best quality for complex analysis

See https://openrouter.ai/models for full list and pricing.

## Troubleshooting

### CrewAI service fails to start
- Check `OPENROUTER_API_KEY` is set correctly
- Verify network connectivity to `https://openrouter.ai`
- Check logs for authentication errors

### Cache not saving requests
- Ensure `CREWAI_LLM_CACHE_ENABLED=true`
- Check cache stats for high miss rate
- Consider increasing `CREWAI_LLM_CACHE_TTL_SECONDS`

### High costs
- Switch to a cheaper model in `CREWAI_LLM_MODEL`
- Increase cache TTL to reuse more responses
- Lower `CREWAI_LLM_TEMPERATURE` for more deterministic outputs (better caching)
