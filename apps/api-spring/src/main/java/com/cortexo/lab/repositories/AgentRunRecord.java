package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Document(collection = "agent_runs")
public record AgentRunRecord(
        @Id String id,
        String agentRunId,
        String taskId,
        String modelVariantId,
        String repositorySnapshotId,
        String status,
        List<AgentEvent> events,
        String finalOutput,
        String patch,
        Map<String, Object> verifier,
        Map<String, Object> usage,
        Instant startedAt,
        Instant finishedAt,
        Instant createdAt) {

    public AgentRunRecord withEvent(AgentEvent event) {
        List<AgentEvent> updated = new java.util.ArrayList<>(events);
        updated.add(event);
        return new AgentRunRecord(id, agentRunId, taskId, modelVariantId, repositorySnapshotId,
                status, updated, finalOutput, patch, verifier, usage, startedAt, finishedAt, createdAt);
    }

    public record AgentEvent(
            String type,
            String tool,
            Object input,
            Object output,
            Instant timestamp) {
    }
}