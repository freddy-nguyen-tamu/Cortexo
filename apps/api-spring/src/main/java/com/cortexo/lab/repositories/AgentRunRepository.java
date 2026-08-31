package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface AgentRunRepository extends MongoRepository<AgentRunRecord, String> {

    Optional<AgentRunRecord> findByAgentRunId(String agentRunId);

    List<AgentRunRecord> findByModelVariantId(String modelVariantId);
}