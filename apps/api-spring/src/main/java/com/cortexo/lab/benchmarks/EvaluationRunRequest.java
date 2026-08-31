package com.cortexo.lab.benchmarks;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.Map;

/**
 * Public evaluation run request. Deliberately contains NO gold/answer-key
 * fields: the trusted task object is loaded server-side by the ML gateway.
 */
public record EvaluationRunRequest(
        @NotBlank String taskId,
        @NotBlank String modelVariantId,
        String repositorySnapshotId,
        @NotNull Integer seed,
        Map<String, Object> generation) {

    public EvaluationRunRequest {
        if (generation == null) {
            generation = Map.of();
        }
    }
}