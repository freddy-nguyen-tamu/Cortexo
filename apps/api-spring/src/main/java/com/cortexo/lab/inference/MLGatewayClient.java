package com.cortexo.lab.inference;

import com.cortexo.lab.benchmarks.EvaluationRunRequest;
import com.cortexo.lab.config.CortexoConfigProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;
import java.util.Map;

@Service
public class MLGatewayClient {

    private static final Logger log = LoggerFactory.getLogger(MLGatewayClient.class);

    private static final Duration EVALUATION_TIMEOUT = Duration.ofSeconds(330);

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

    public Map<String, Object> listEvaluationTasks() {
        try {
            Map<String, Object> wrapped = mlGatewayClient.get()
                    .uri("/v1/evaluations/tasks")
                    .retrieve()
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {
                    })
                    .timeout(Duration.ofSeconds(15))
                    .block();
            return unwrap(wrapped);
        } catch (Exception e) {
            log.warn("ML gateway evaluation task list unavailable", e);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "ML gateway unavailable: " + e.getMessage());
        }
    }

    public Map<String, Object> runEvaluation(EvaluationRunRequest request) {
        log.info("calling ML gateway evaluation taskId={} modelVariantId={}", request.taskId(), request.modelVariantId());
        try {
            Map<String, Object> wrapped = mlGatewayClient.post()
                    .uri("/v1/evaluations/run")
                    .contentType(MediaType.APPLICATION_JSON)
                    .bodyValue(request)
                    .retrieve()
                    .onStatus(status -> status.value() == 503,
                            response -> response.bodyToMono(String.class).map(body -> {
                                log.warn("ML gateway grader disabled: {}", body);
                                return new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
                                        "executable grader is disabled on the ML gateway");
                            }))
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {
                    })
                    .timeout(EVALUATION_TIMEOUT)
                    .block();
            return unwrap(wrapped);
        } catch (ResponseStatusException e) {
            log.warn("ML gateway rejected evaluation taskId={}: {}", request.taskId(), e.getReason());
            throw e;
        } catch (Exception e) {
            log.warn("ML gateway evaluation failed taskId={}", request.taskId(), e);
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "ML gateway evaluation failed: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> unwrap(Map<String, Object> wrapped) {
        if (wrapped == null) {
            throw new ResponseStatusException(HttpStatus.BAD_GATEWAY, "ML gateway returned no payload");
        }
        Object data = wrapped.get("data");
        if (data instanceof Map<?, ?>) {
            return (Map<String, Object>) data;
        }
        return wrapped;
    }

    public Map<String, Object> latestRegressionReport() {
        try {
            Map<String, Object> wrapped = mlGatewayClient.get()
                    .uri("/v1/regression/latest")
                    .retrieve()
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {
                    })
                    .timeout(Duration.ofSeconds(10))
                    .block();
            return unwrap(wrapped);
        } catch (Exception e) {
            log.warn("ML gateway regression report unavailable", e);
            return Map.of("available", false, "error", e.getClass().getSimpleName());
        }
    }

    public Map<String, Object> regressionHistory(int limit) {
        try {
            Map<String, Object> wrapped = mlGatewayClient.get()
                    .uri(uriBuilder -> uriBuilder.path("/v1/regression/history")
                            .queryParam("limit", limit)
                            .build())
                    .retrieve()
                    .bodyToMono(new org.springframework.core.ParameterizedTypeReference<Map<String, Object>>() {
                    })
                    .timeout(Duration.ofSeconds(10))
                    .block();
            return unwrap(wrapped);
        } catch (Exception e) {
            log.warn("ML gateway regression history unavailable", e);
            return Map.of("available", false, "error", e.getClass().getSimpleName());
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