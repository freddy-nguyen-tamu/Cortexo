package com.cortexo.lab.inference;

import com.cortexo.lab.common.ApiResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api/inference")
public class InferenceController {

    private final MLGatewayClient mlGatewayClient;

    public InferenceController(MLGatewayClient mlGatewayClient) {
        this.mlGatewayClient = mlGatewayClient;
    }

    @PostMapping("/generate")
    public ApiResponse<Map<String, Object>> generate(@Valid @RequestBody GenerateRequest request) {
        return ApiResponse.ok(mlGatewayClient.generate(request));
    }
}