package com.cortexo.lab.models;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface ModelRegistryRepository extends MongoRepository<ModelRecord, String> {

    Optional<ModelRecord> findByModelId(String modelId);

    List<ModelRecord> findByFamily(String family);

    List<ModelRecord> findByParentModelId(String parentModelId);

    boolean existsByModelId(String modelId);
}