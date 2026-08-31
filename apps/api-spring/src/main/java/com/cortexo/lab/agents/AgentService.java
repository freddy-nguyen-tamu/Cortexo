package com.cortexo.lab.agents;

import com.cortexo.lab.common.ApiException;
import com.cortexo.lab.repositories.AgentRunRecord;
import com.cortexo.lab.repositories.AgentRunRepository;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Map;
import java.util.UUID;

@Service
public class AgentService {

    private final AgentRunRepository agentRuns;

    public AgentService(AgentRunRepository agentRuns) {
        this.agentRuns = agentRuns;
    }

    public AgentRunRecord createRun(AgentRunRequest request) {
        if (request.taskId() == null || request.taskId().isBlank()) {
            throw ApiException.badRequest("taskId is required");
        }
        if (request.modelVariantId() == null || request.modelVariantId().isBlank()) {
            throw ApiException.badRequest("modelVariantId is required");
        }
        AgentRunRecord record = new AgentRunRecord(
                UUID.randomUUID().toString(),
                "agent-" + UUID.randomUUID().toString().substring(0, 8),
                request.taskId(),
                request.modelVariantId(),
                request.repositorySnapshotId(),
                "STARTED",
                new ArrayList<>(),
                null,
                null,
                Map.of(),
                Map.of(),
                Instant.now(),
                null,
                Instant.now());
        return agentRuns.save(record);
    }

    public AgentRunRecord appendEvent(String agentRunId, AgentRunRecord.AgentEvent event) {
        AgentRunRecord existing = agentRuns.findById(agentRunId)
                .orElseThrow(() -> ApiException.notFound("agent run not found: " + agentRunId));
        return agentRuns.save(existing.withEvent(event));
    }

    public AgentRunRecord get(String agentRunId) {
        return agentRuns.findByAgentRunId(agentRunId)
                .orElseThrow(() -> ApiException.notFound("agent run not found: " + agentRunId));
    }

    public record AgentRunRequest(
            String taskId,
            String modelVariantId,
            String repositorySnapshotId,
            Map<String, Object> config) {
    }
}