package com.cortexo.lab.inference;

import com.cortexo.lab.config.CortexoConfigProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;

import java.time.Duration;
import java.util.Map;

@Service
public class MLGatewayClient {

    private static final Logger log = LoggerFactory.getLogger(MLGatewayClient.class);

    private final WebClient mlGatewayClient;
    private final Duration timeout;

    public MLGatewayClient(WebClient mlGatewayClient, CortexoConfigProperties props) {
        this.mlGatewayClient = mlGatewayClient;
        this.timeout = Duration.ofSeconds(30);
    }

    public Map<String, Object> generate(GenerateRequest request) {
        log.info("calling ML gateway generate taskId={} modelVariantId={} requestId={}",
                request.taskId(), request.modelVariantId(), request.requestId());
        try {
            return mlGatewayClient.post()
                    .uri("/v1/inference/generate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .retrieve()
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {
                    })
                    .timeout(timeout)
                    .block();
        } catch (Exception e) {
            log.warn("ML gateway request failed; returning degraded result requestId={}", request.requestId(), e);
            return Map.of(
                    "requestId", request.requestId(),
                    "modelVariantId", request.modelVariantId(),
                    "output", "[" + e.getClass().getSimpleName() + "] unable to reach ML gateway",
                    "structuredOutput", Map.of(),
                    "usage", Map.of("latencyMs", 0),
                    "trace", Map.of("retrievalIds", java.util.List.of(),
                            "toolCalls", java.util.List.of(),
                            "warnings", java.util.List.of("ml gateway unavailable")));
        }
    }

    public Map<String, Object> health() {
        try {
            return mlGatewayClient.get()
                    .uri("/health")
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(Duration.ofSeconds(5))
                    .block();
        } catch (Exception e) {
            return Map.of("status", "unreachable", "error", e.getClass().getSimpleName());
        }
    }
}