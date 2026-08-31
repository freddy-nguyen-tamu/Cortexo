package com.cortexo.lab.repositories;

import com.cortexo.lab.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/repositories")
public class RepositoryController {

    private final RepositoryService service;

    public RepositoryController(RepositoryService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<List<RepositoryRecord>> list() {
        return ApiResponse.ok(service.list());
    }

    @PostMapping
    public ApiResponse<RepositoryRecord> register(@RequestBody RepositoryRecord record) {
        return ApiResponse.ok(service.register(record));
    }

    @PostMapping("/{repositoryId}/snapshots")
    public ApiResponse<RepositorySnapshot> ingest(@PathVariable String repositoryId) {
        return ApiResponse.ok(service.createSnapshot(repositoryId, "dev"));
    }

    @GetMapping("/{repositoryId}/snapshots")
    public ApiResponse<List<RepositorySnapshot>> snapshots(@PathVariable String repositoryId) {
        return ApiResponse.ok(service.snapshots(repositoryId));
    }
}