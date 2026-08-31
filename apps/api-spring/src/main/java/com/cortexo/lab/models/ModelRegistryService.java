package com.cortexo.lab.models;

import com.cortexo.lab.common.ApiException;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ModelRegistryService {

    private final ModelRegistryRepository models;

    public ModelRegistryService(ModelRegistryRepository models) {
        this.models = models;
    }

    public ModelRecord register(ModelRecord model) {
        if (model.getModelId() == null || model.getModelId().isBlank()) {
            throw ApiException.badRequest("modelId is required");
        }
        if (models.existsByModelId(model.getModelId())) {
            throw ApiException.badRequest("modelId already registered: " + model.getModelId());
        }
        return models.save(model);
    }

    public List<ModelRecord> listAll() {
        return models.findAll();
    }

    public ModelRecord getByModelId(String modelId) {
        return models.findByModelId(modelId).orElseThrow(
                () -> ApiException.notFound("model not found: " + modelId));
    }

    public List<ModelRecord> childrenOf(String modelId) {
        return models.findByParentModelId(modelId);
    }
}