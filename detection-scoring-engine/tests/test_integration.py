"""Integration tests for the detection service."""
import pytest


class TestIntegration:
    """Integration tests requiring full service startup."""

    @pytest.mark.skip(reason="Requires Kafka and OpenSearch running")
    def test_end_to_end_flow(self):
        """Test end-to-end flow from Kafka to detection."""
        # This test requires:
        # 1. Kafka with normalized-activity topic
        # 2. OpenSearch with logs-* indices
        # 3. Publishing a normalized event
        # 4. Verifying detection is created
        # 5. Verifying detection is indexed to OS
        # 6. Verifying detection is published to Kafka
        pass

    @pytest.mark.skip(reason="Requires Kafka and OpenSearch running")
    def test_alerts_api_integration(self):
        """Test alerts API with real data."""
        # This test requires:
        # 1. Detection service running
        # 2. OpenSearch with detection indices
        # 3. Querying /v1/alerts
        # 4. Verifying response format
        pass
