package com.cortexo.lab.experiments;

import com.cortexo.lab.common.ApiException;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class ExperimentService {

    private final ExperimentRepository experiments;

    public ExperimentService(ExperimentRepository experiments) {
        this.experiments = experiments;
    }

    public ExperimentRecord create(ExperimentRecord record) {
        if (record.modelVariantIds() == null || record.modelVariantIds().isEmpty()) {
            throw ApiException.badRequest("at least one modelVariantId is required");
        }
        if (record.taskIds() == null || record.taskIds().isEmpty()) {
            throw ApiException.badRequest("at least one taskId is required");
        }
        return experiments.save(new ExperimentRecord(
                UUID.randomUUID().toString(),
                record.experimentId() == null ? "exp-" + UUID.randomUUID().toString().substring(0, 8) : record.experimentId(),
                record.name(),
                record.repositorySnapshotId(),
                record.modelVariantIds(),
                record.taskIds(),
                record.seed() == null ? 42 : record.seed(),
                record.generationSettings() == null ? Map.of() : record.generationSettings(),
                record.config() == null ? Map.of() : record.config(),
                "CREATED",
                Instant.now()));
    }

    public List<ExperimentRecord> listAll() {
        return experiments.findAll();
    }

    public ExperimentRecord get(String experimentId) {
        return experiments.findByExperimentId(experimentId)
                .orElseThrow(() -> ApiException.notFound("experiment not found: " + experimentId));
    }
}