package com.cortexo.lab.models;

import com.cortexo.lab.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/models")
public class ModelRegistryController {

    private final ModelRegistryService registry;

    public ModelRegistryController(ModelRegistryService registry) {
        this.registry = registry;
    }

    @GetMapping
    public ApiResponse<List<ModelRecord>> list() {
        return ApiResponse.ok(registry.listAll());
    }

    @GetMapping("/{modelId}")
    public ApiResponse<ModelRecord> get(@PathVariable String modelId) {
        return ApiResponse.ok(registry.getByModelId(modelId));
    }

    @GetMapping("/{modelId}/lineage")
    public ApiResponse<List<ModelRecord>> lineage(@PathVariable String modelId) {
        return ApiResponse.ok(registry.childrenOf(modelId));
    }

    @PostMapping
    public ApiResponse<ModelRecord> register(@RequestBody ModelRecord record) {
        return ApiResponse.ok(registry.register(record));
    }
}