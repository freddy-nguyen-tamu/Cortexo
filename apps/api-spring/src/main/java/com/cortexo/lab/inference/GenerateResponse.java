package com.cortexo.lab.inference;

import java.util.Map;

public record GenerateResponse(
        String requestId,
        String modelVariantId,
        String output,
        Map<String, Object> structuredOutput,
        Map<String, Object> usage,
        Trace trace) {

    public record Trace(
            java.util.List<String> retrievalIds,
            java.util.List<Object> toolCalls,
            java.util.List<String> warnings) {
    }
}