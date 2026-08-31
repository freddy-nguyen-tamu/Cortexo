package com.cortexo.lab.common;

import com.cortexo.lab.inference.MLGatewayClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

@RestController
public class HealthController {

    private final MLGatewayClient mlGatewayClient;

    public HealthController(MLGatewayClient mlGatewayClient) {
        this.mlGatewayClient = mlGatewayClient;
    }

    @GetMapping("/api/health")
    public Map<String, Object> health() {
        return Map.of(
                "status", "up",
                "service", "cortexo-api",
                "time", Instant.now().toString(),
                "mlGateway", mlGatewayClient.health());
    }
}