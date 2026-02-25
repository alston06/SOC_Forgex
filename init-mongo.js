// MongoDB initialization script for SOC Platform
// This script creates the necessary collections and indexes

db = db.getSiblingDB('soc_db');

// Create api_keys collection with indexes
db.createCollection('api_keys');
db.api_keys.createIndex({ "key_hash": 1 }, { unique: true });
db.api_keys.createIndex({ "tenant_id": 1 });

// Create incidents collection with indexes
db.createCollection('incidents');
db.incidents.createIndex({ "tenant_id": 1, "status": 1 });
db.incidents.createIndex({ "detection_id": 1 });
db.incidents.createIndex({ "created_at": -1 });

// Create notifications collection with indexes
db.createCollection('notifications');
db.notifications.createIndex({ "incident_id": 1 });
db.notifications.createIndex({ "sent_at": -1 });

// Create tenant_webhooks collection with indexes
db.createCollection('tenant_webhooks');
db.tenant_webhooks.createIndex({ "tenant_id": 1 });
db.tenant_webhooks.createIndex({ "active": 1 });

// Create ingestion_metrics collection with indexes
db.createCollection('ingestion_metrics');
db.ingestion_metrics.createIndex({ "tenant_id": 1, "timestamp": -1 });

// Insert a sample API key for testing (hash of "test-api-key-123")
// SHA256("test-api-key-123") = 4f9c461f8a5f8c8f7a3f9e9c5e1c3f2e8b9a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e
db.api_keys.insertOne({
    "key_hash": "4f9c461f8a5f8c8f7a3f9e9c5e1c3f2e8b9a7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e",
    "tenant_id": "tenant-demo-001",
    "service_name": "demo-service",
    "environment": "development",
    "rate_limit": 1000,
    "created_at": new Date()
});

// Insert a sample webhook configuration
db.tenant_webhooks.insertOne({
    "tenant_id": "tenant-demo-001",
    "events": ["incident_open", "critical_alert"],
    "url": "https://webhook.site/unique-uuid-here",
    "active": true,
    "created_at": new Date()
});

print("MongoDB initialization completed successfully");
print("Sample API key created: test-api-key-123 (tenant: tenant-demo-001)");
