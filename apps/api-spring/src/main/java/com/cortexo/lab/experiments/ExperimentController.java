package com.cortexo.lab.experiments;

import com.cortexo.lab.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/experiments")
public class ExperimentController {

    private final ExperimentService service;

    public ExperimentController(ExperimentService service) {
        this.service = service;
    }

    @PostMapping
    public ApiResponse<ExperimentRecord> create(@RequestBody ExperimentRecord record) {
        return ApiResponse.ok(service.create(record));
    }

    @GetMapping
    public ApiResponse<List<ExperimentRecord>> list() {
        return ApiResponse.ok(service.listAll());
    }

    @GetMapping("/{experimentId}")
    public ApiResponse<ExperimentRecord> get(@PathVariable String experimentId) {
        return ApiResponse.ok(service.get(experimentId));
    }
}