package com.cortexo.lab.models;

import com.cortexo.lab.common.ApiException;
import com.cortexo.lab.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/registry")
public class ResourceRegistryController {

    private final TokenizerRepository tokenizers;
    private final DatasetRepository datasets;

    public ResourceRegistryController(TokenizerRepository tokenizers, DatasetRepository datasets) {
        this.tokenizers = tokenizers;
        this.datasets = datasets;
    }

    @GetMapping("/tokenizers")
    public ApiResponse<List<TokenizerRecord>> listTokenizers() {
        return ApiResponse.ok(tokenizers.findAll());
    }

    @PostMapping("/tokenizers")
    public ApiResponse<TokenizerRecord> registerTokenizer(@RequestBody TokenizerRecord record) {
        if (record.getTokenizerId() == null || record.getTokenizerId().isBlank()) {
            throw ApiException.badRequest("tokenizerId is required");
        }
        if (tokenizers.findByTokenizerId(record.getTokenizerId()).isPresent()) {
            throw ApiException.badRequest("tokenizerId already registered");
        }
        return ApiResponse.ok(tokenizers.save(record));
    }

    @GetMapping("/datasets")
    public ApiResponse<List<DatasetRecord>> listDatasets() {
        return ApiResponse.ok(datasets.findAll());
    }

    @PostMapping("/datasets")
    public ApiResponse<DatasetRecord> registerDataset(@RequestBody DatasetRecord record) {
        if (record.getDatasetId() == null || record.getDatasetId().isBlank()) {
            throw ApiException.badRequest("datasetId is required");
        }
        return ApiResponse.ok(datasets.save(record));
    }

    @GetMapping("/datasets/{datasetId}/{version}")
    public ApiResponse<DatasetRecord> getDataset(@PathVariable String datasetId,
                                                 @PathVariable String version) {
        return ApiResponse.ok(datasets.findByDatasetIdAndVersion(datasetId, version)
                .orElseThrow(() -> ApiException.notFound("dataset not found: " + datasetId + "@" + version)));
    }
}