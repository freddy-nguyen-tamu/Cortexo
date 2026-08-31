package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Document(collection = "retrieval_runs")
public record RetrievalRunRecord(
        @Id String id,
        String retrievalRunId,
        String taskId,
        String modelVariantId,
        String repositorySnapshotId,
        String query,
        String strategy,
        List<Map<String, Object>> stages,
        Map<String, Object> contextPack,
        Instant createdAt) {
}