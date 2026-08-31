package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Document(collection = "router_decisions")
public record RouterDecisionRecord(
        @Id String id,
        String requestId,
        String taskId,
        String repositorySnapshotId,
        Map<String, Object> features,
        List<Map<String, Object>> candidates,
        String selected,
        Instant createdAt) {
}