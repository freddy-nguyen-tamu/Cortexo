package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;

@Document(collection = "repository_snapshots")
public record RepositorySnapshot(
        @Id String id,
        String repositoryId,
        String commitSha,
        String pipelineVersion,
        long fileCount,
        long symbolCount,
        long chunkCount,
        long graphNodeCount,
        long graphEdgeCount,
        String status,
        Instant createdAt) {

    public RepositorySnapshot withCounts(long fileCount, long symbolCount, long chunkCount,
                                         long graphNodeCount, long graphEdgeCount) {
        return new RepositorySnapshot(id, repositoryId, commitSha, pipelineVersion,
                fileCount, symbolCount, chunkCount, graphNodeCount, graphEdgeCount,
                status, createdAt);
    }

    public RepositorySnapshot withStatus(String newStatus) {
        return new RepositorySnapshot(id, repositoryId, commitSha, pipelineVersion,
                fileCount, symbolCount, chunkCount, graphNodeCount, graphEdgeCount,
                newStatus, createdAt);
    }
}