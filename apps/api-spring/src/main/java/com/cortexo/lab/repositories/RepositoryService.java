package com.cortexo.lab.repositories;

import com.cortexo.lab.common.ApiException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
public class RepositoryService {

    private final RepositoryRepository repositories;
    private final RepositorySnapshotRepository snapshots;

    public RepositoryService(RepositoryRepository repositories,
                             RepositorySnapshotRepository snapshots) {
        this.repositories = repositories;
        this.snapshots = snapshots;
    }

    public RepositoryRecord register(RepositoryRecord record) {
        if (record.name() == null || record.name().isBlank()) {
            throw ApiException.badRequest("repository name is required");
        }
        if (record.license() == null || record.license().isBlank()) {
            throw ApiException.badRequest("repository license is required");
        }
        RepositoryRecord saved = repositories.save(new RepositoryRecord(
                UUID.randomUUID().toString(),
                record.name(),
                record.url(),
                record.description(),
                record.license(),
                record.licenseVerified(),
                record.languages() == null ? List.of() : record.languages(),
                record.ownerUserId(),
                "REGISTERED",
                Instant.now()));
        return saved;
    }

    public RepositorySnapshot createSnapshot(String repositoryId, String pipelineVersion) {
        RepositoryRecord repo = repositories.findById(repositoryId)
                .orElseThrow(() -> ApiException.notFound("repository not found: " + repositoryId));
        if (!"REGISTERED".equals(repo.status()) && !"FAILED".equals(repo.status())) {
            throw ApiException.badRequest("repository already has an ingestion in progress");
        }

        RepositorySnapshot snapshot = snapshots.save(new RepositorySnapshot(
                UUID.randomUUID().toString(),
                repositoryId,
                null,
                pipelineVersion == null ? "dev" : pipelineVersion,
                0,
                0,
                0,
                0,
                0,
                "INDEXING",
                Instant.now()));
        repositories.save(repo.withStatus("INGESTING"));
        return snapshot;
    }

    public RepositorySnapshot markSnapshotReady(String snapshotId, long fileCount, long symbolCount,
                                                long chunkCount, long graphNodeCount, long graphEdgeCount) {
        RepositorySnapshot snapshot = snapshots.findById(snapshotId)
                .orElseThrow(() -> ApiException.notFound("snapshot not found: " + snapshotId));
        RepositorySnapshot updated = snapshot
                .withCounts(fileCount, symbolCount, chunkCount, graphNodeCount, graphEdgeCount)
                .withStatus("READY");
        snapshots.save(updated);
        repositories.findById(snapshot.repositoryId())
                .ifPresent(repo -> repositories.save(repo.withStatus("INDEXED")));
        return updated;
    }

    public RepositorySnapshot markSnapshotFailed(String snapshotId, String commitSha) {
        RepositorySnapshot snapshot = snapshots.findById(snapshotId)
                .orElseThrow(() -> ApiException.notFound("snapshot not found: " + snapshotId));
        RepositorySnapshot updated = new RepositorySnapshot(
                snapshot.id(), snapshot.repositoryId(), commitSha, snapshot.pipelineVersion(),
                snapshot.fileCount(), snapshot.symbolCount(), snapshot.chunkCount(),
                snapshot.graphNodeCount(), snapshot.graphEdgeCount(), "FAILED", snapshot.createdAt());
        snapshots.save(updated);
        repositories.findById(snapshot.repositoryId())
                .ifPresent(repo -> repositories.save(repo.withStatus("FAILED")));
        return updated;
    }

    public List<RepositoryRecord> list() {
        return repositories.findAll();
    }

    public List<RepositorySnapshot> snapshots(String repositoryId) {
        return snapshots.findByRepositoryId(repositoryId);
    }
}