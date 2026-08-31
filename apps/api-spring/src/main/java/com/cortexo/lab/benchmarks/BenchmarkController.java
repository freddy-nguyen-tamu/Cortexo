package com.cortexo.lab.benchmarks;

import com.cortexo.lab.common.ApiResponse;
import com.cortexo.lab.inference.MLGatewayClient;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/benchmarks")
public class BenchmarkController {

    private final BenchmarkService service;
    private final MLGatewayClient mlGatewayClient;

    public BenchmarkController(BenchmarkService service, MLGatewayClient mlGatewayClient) {
        this.service = service;
        this.mlGatewayClient = mlGatewayClient;
    }

    @GetMapping("/suites")
    public ApiResponse<List<BenchmarkSuite>> suites() {
        return ApiResponse.ok(service.listSuites());
    }

    @PostMapping("/suites")
    public ApiResponse<BenchmarkSuite> createSuite(@RequestBody Map<String, String> body) {
        return ApiResponse.ok(service.registerSuite(body.get("id"), body.get("name"),
                body.getOrDefault("version", "v1")));
    }

    @GetMapping("/suites/{suiteId}/tasks")
    public ApiResponse<List<BenchmarkTask>> tasks(@PathVariable String suiteId) {
        return ApiResponse.ok(service.tasksOfSuite(suiteId));
    }

    @GetMapping("/models/{modelVariantId}/runs")
    public ApiResponse<List<BenchmarkRun>> modelRuns(@PathVariable String modelVariantId) {
        return ApiResponse.ok(service.runsOfModel(modelVariantId));
    }

    @GetMapping("/evaluations/tasks")
    public ApiResponse<Map<String, Object>> evaluationTasks() {
        return ApiResponse.ok(mlGatewayClient.listEvaluationTasks());
    }

    @PostMapping("/evaluations/run")
    public ApiResponse<Map<String, Object>> runEvaluation(@Valid @RequestBody EvaluationRunRequest request) {
        return ApiResponse.ok(mlGatewayClient.runEvaluation(request));
    }

    @GetMapping("/regression/latest")
    public ApiResponse<Map<String, Object>> regressionLatest() {
        return ApiResponse.ok(mlGatewayClient.latestRegressionReport());
    }

    @GetMapping("/regression/history")
    public ApiResponse<Map<String, Object>> regressionHistory(
            @RequestParam(defaultValue = "20") int limit) {
        int clamped = Math.max(1, Math.min(limit, 100));
        return ApiResponse.ok(mlGatewayClient.regressionHistory(clamped));
    }
}