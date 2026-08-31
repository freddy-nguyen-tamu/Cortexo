package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.Map;

@Document(collection = "training_runs")
public record TrainingRunRecord(
        @Id String id,
        String runId,
        String modelVariantId,
        String datasetId,
        String tokenizerId,
        String status,
        Map<String, Object> config,
        Map<String, Object> summary,
        Instant createdAt) {

    public TrainingRunRecord withStatus(String newStatus) {
        return new TrainingRunRecord(id, runId, modelVariantId, datasetId,
                tokenizerId, newStatus, config, summary, createdAt);
    }
}