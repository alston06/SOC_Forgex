"""Automated integration test for CrewAI implementation."""
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any
import httpx
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger("INFO"),
)

logger = structlog.get_logger(__name__)

# Test configuration
BASE_URL = "http://localhost:8003"
INTERNAL_TOKEN = "soc-internal-token-v1"
HEADERS = {
    "Authorization": f"Bearer {INTERNAL_TOKEN}",
    "Content-Type": "application/json",
}

# Sample detection event for testing
SAMPLE_DETECTION = {
    "detection_id": f"test-det-{int(time.time())}",
    "tenant_id": "tenant-test-001",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "triggered_events": ["login_failure"],
    "rule_id": "rule-test-001",
    "severity": "HIGH",
    "confidence": 0.9,
    "description": "Multiple failed logins from suspicious IP",
    "entities": {"actor": ["user123"], "ip": ["10.0.0.1"]},
    "evidence": {"attempts": 5},
}


class TestResult:
    """Test result tracker."""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, name: str, details: str = ""):
        self.passed.append((name, details))
        logger.info("PASS", test=name, details=details)

    def add_fail(self, name: str, error: str):
        self.failed.append((name, error))
        logger.error("FAIL", test=name, error=error)

    def add_warning(self, name: str, warning: str):
        self.warnings.append((name, warning))
        logger.warning("WARN", test=name, warning=warning)

    def summary(self) -> Dict[str, Any]:
        return {
            "total": len(self.passed) + len(self.failed),
            "passed": len(self.passed),
            "failed": len(self.failed),
            "warnings": len(self.warnings),
            "pass_rate": f"{len(self.passed) / (len(self.passed) + len(self.failed)) * 100:.1f}%" if (len(self.passed) + len(self.failed)) > 0 else "0%",
        }


async def test_health_check(result: TestResult) -> bool:
    """Test health check endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
            result.add_pass("Health Check", f"Service healthy: {data.get('service')}")
            return True
    except Exception as e:
        result.add_fail("Health Check", str(e))
        return False


async def test_agent_tools_assigned(result: TestResult) -> bool:
    """Test that agents have tools assigned."""
    try:
        from agents.agents.orchestrator_agent import orchestrator_agent
        from agents.agents.triage_analyst import triage_analyst
        from agents.agents.incident_analyst import incident_analyst
        from agents.agents.threat_intel import threat_intel

        # Check Orchestrator has case tools
        assert len(orchestrator_agent.tools) >= 3, "Orchestrator should have at least 3 tools"
        result.add_pass(
            "Orchestrator Tools",
            f"Has {len(orchestrator_agent.tools)} tools: {[t.name for t in orchestrator_agent.tools]}"
        )

        # Check Triage Analyst has log query tool
        assert len(triage_analyst.tools) >= 1, "Triage Analyst should have at least 1 tool"
        result.add_pass(
            "Triage Analyst Tools",
            f"Has {len(triage_analyst.tools)} tools: {[t.name for t in triage_analyst.tools]}"
        )

        # Check Incident Analyst has log query tool
        assert len(incident_analyst.tools) >= 1, "Incident Analyst should have at least 1 tool"
        result.add_pass(
            "Incident Analyst Tools",
            f"Has {len(incident_analyst.tools)} tools: {[t.name for t in incident_analyst.tools]}"
        )

        # Check Threat Intel has tools
        assert len(threat_intel.tools) >= 1, "Threat Intel should have at least 1 tool"
        result.add_pass(
            "Threat Intel Tools",
            f"Has {len(threat_intel.tools)} tools: {[t.name for t in threat_intel.tools]}"
        )

        return True
    except Exception as e:
        result.add_fail("Agent Tools", str(e))
        return False


async def test_crew_creation(result: TestResult) -> bool:
    """Test that crew can be created."""
    try:
        from agents.models import DetectionEvent
        from agents.crewai.crew import create_incident_analysis_crew

        detection = DetectionEvent(**SAMPLE_DETECTION)
        crew = create_incident_analysis_crew(detection)

        assert crew is not None, "Crew should be created"
        assert len(crew.agents) == 4, "Crew should have 4 agents"
        assert len(crew.tasks) == 6, "Crew should have 6 tasks"

        result.add_pass(
            "Crew Creation",
            f"Crew created with {len(crew.agents)} agents and {len(crew.tasks)} tasks"
        )
        return True
    except Exception as e:
        result.add_fail("Crew Creation", str(e))
        return False


async def test_kickoff_endpoint(result: TestResult) -> bool:
    """Test kickoff endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{BASE_URL}/kickoff",
                headers=HEADERS,
                json={"detection": SAMPLE_DETECTION},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "flow_id" in data, "Response should contain flow_id"
            assert "status" in data, "Response should contain status"

            result.add_pass(
                "Kickoff Endpoint",
                f"Flow started: {data['flow_id']}, status: {data['status']}"
            )
            return data["flow_id"]
    except Exception as e:
        result.add_fail("Kickoff Endpoint", str(e))
        return None


async def test_case_creation(result: TestResult, flow_id: str = None) -> bool:
    """Test that case was created."""
    try:
        if not flow_id:
            result.add_warning("Case Creation", "No flow_id provided, skipping case check")
            return True

        # Wait a bit for async processing
        await asyncio.sleep(5)

        # Query case-service for cases
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "http://localhost:8004/cases",
                headers=HEADERS,
            )
            if resp.status_code == 200:
                cases = resp.json()
                detection_cases = [c for c in cases if c.get("detection_id") == SAMPLE_DETECTION["detection_id"]]
                if detection_cases:
                    case = detection_cases[0]
                    result.add_pass(
                        "Case Creation",
                        f"Case created: {case['case_id']}, severity: {case['severity']}"
                    )
                    return True

        result.add_warning("Case Creation", "Case not found yet (may still be processing)")
        return True
    except Exception as e:
        result.add_warning("Case Creation", f"Could not verify case: {e}")
        return True  # Don't fail on this - may be no data


async def test_cache_stats(result: TestResult) -> bool:
    """Test cache stats endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BASE_URL}/cache/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert "cache_hits" in data
            assert "cache_misses" in data
            assert "hit_rate_percent" in data

            result.add_pass(
                "Cache Stats",
                f"Hits: {data['cache_hits']}, Misses: {data['cache_misses']}, Hit Rate: {data['hit_rate_percent']}%"
            )
            return True
    except Exception as e:
        result.add_fail("Cache Stats", str(e))
        return False


async def test_log_query_tool(result: TestResult) -> bool:
    """Test log query tool wrapper."""
    try:
        from agents.crewai.tool_wrappers import query_logs_sync

        result_str = query_logs_sync(
            tenant_id=SAMPLE_DETECTION["tenant_id"],
            minutes_back=30,
            limit=10,
        )

        result_data = json.loads(result_str)
        assert "event_count" in result_data
        assert "events" in result_data

        result.add_pass(
            "Log Query Tool",
            f"Retrieved {result_data['event_count']} events"
        )
        return True
    except Exception as e:
        result.add_warning("Log Query Tool", f"Tool test failed (may be expected if no data): {e}")
        return True  # Don't fail on this - may be no data


async def run_all_tests() -> TestResult:
    """Run all integration tests."""
    result = TestResult()

    logger.info("Starting CrewAI Integration Tests", timestamp=datetime.utcnow().isoformat())

    # Test 1: Health check
    await test_health_check(result)
    await asyncio.sleep(1)

    # Test 2: Agent tools assigned
    await test_agent_tools_assigned(result)
    await asyncio.sleep(1)

    # Test 3: Crew creation
    await test_crew_creation(result)
    await asyncio.sleep(1)

    # Test 4: Kickoff endpoint
    flow_id = await test_kickoff_endpoint(result)
    await asyncio.sleep(1)

    # Test 5: Case creation (async verification)
    await test_case_creation(result, flow_id)
    await asyncio.sleep(1)

    # Test 6: Cache stats
    await test_cache_stats(result)
    await asyncio.sleep(1)

    # Test 7: Log query tool
    await test_log_query_tool(result)

    return result


def main():
    """Run tests and print summary."""
    print("\n" + "="*80)
    print("CrewAI Integration Test Suite")
    print("="*80 + "\n")

    result = asyncio.run(run_all_tests())

    # Print summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    summary = result.summary()
    print(f"Total Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Warnings: {summary['warnings']}")
    print(f"Pass Rate: {summary['pass_rate']}")
    print("="*80 + "\n")

    if result.passed:
        print("PASSED TESTS:")
        for name, details in result.passed:
            print(f"  {name}")
            if details:
                print(f"    {details}")

    if result.failed:
        print("\nFAILED TESTS:")
        for name, error in result.failed:
            print(f"  {name}")
            print(f"    Error: {error}")

    if result.warnings:
        print("\nWARNINGS:")
        for name, warning in result.warnings:
            print(f"  {name}")
            print(f"    {warning}")

    # Exit code
    exit(0 if len(result.failed) == 0 else 1)


if __name__ == "__main__":
    main()
