package com.cortexo.lab.storage.cassandra;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.Map;

/**
 * Cassandra is used only for append-heavy telemetry and is kept local/optional.
 * <p>
 * Keyspace: cortexo_telemetry
 * <pre>
 * training_events_by_run           PRIMARY KEY ((run_id), step)
 * inference_events_by_model_day    PRIMARY KEY ((model_id, event_day), event_time, request_id)
 * agent_events_by_run              PRIMARY KEY ((agent_run_id), event_index)
 * retrieval_events_by_run          PRIMARY KEY ((retrieval_run_id), stage, rank)
 * </pre>
 * Implementation is intentionally deferred until the normal JSONL/Mongo
 * tracking pipeline works. This class only reports configuration status so the
 * storage dashboard can render it.
 */
@Service
public class CassandraTelemetryService {

    private final boolean enabled;
    private final String contactPoints;

    public CassandraTelemetryService(
            @Value("${CASSANDRA_ENABLED:false}") boolean enabled,
            @Value("${CASSANDRA_CONTACT_POINTS:localhost:9042}") String contactPoints) {
        this.enabled = enabled;
        this.contactPoints = contactPoints;
    }

    public Map<String, Object> status() {
        return Map.of(
                "id", "cassandra",
                "role", "high-volume telemetry",
                "enabled", enabled,
                "contactPoints", contactPoints,
                "keyspace", "cortexo_telemetry",
                "implementation", "deferred-until-jsonl-mongo-tracking-works");
    }
}