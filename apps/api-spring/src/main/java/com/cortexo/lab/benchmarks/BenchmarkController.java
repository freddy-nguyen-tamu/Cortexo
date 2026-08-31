package com.cortexo.lab.benchmarks;

import com.cortexo.lab.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/benchmarks")
public class BenchmarkController {

    private final BenchmarkService service;

    public BenchmarkController(BenchmarkService service) {
        this.service = service;
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
}