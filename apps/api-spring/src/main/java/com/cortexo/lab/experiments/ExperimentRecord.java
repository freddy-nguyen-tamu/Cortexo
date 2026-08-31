package com.cortexo.lab.experiments;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Document(collection = "experiments")
public record ExperimentRecord(
        @Id String id,
        String experimentId,
        String name,
        String repositorySnapshotId,
        List<String> modelVariantIds,
        List<String> taskIds,
        Integer seed,
        Map<String, Object> generationSettings,
        Map<String, Object> config,
        String status,
        Instant createdAt) {

    public ExperimentRecord withStatus(String newStatus) {
        return new ExperimentRecord(id, experimentId, name, repositorySnapshotId,
                modelVariantIds, taskIds, seed, generationSettings, config,
                newStatus, createdAt);
    }
}