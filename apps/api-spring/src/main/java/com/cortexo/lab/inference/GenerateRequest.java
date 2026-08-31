package com.cortexo.lab.inference;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.Map;

public record GenerateRequest(
        @NotBlank String requestId,
        @NotBlank String modelVariantId,
        String repositorySnapshotId,
        String taskId,
        @NotBlank String prompt,
        @NotNull Integer seed,
        Map<String, Object> generation) {

    public GenerateRequest {
        if (generation == null) {
            generation = Map.of();
        }
    }
}