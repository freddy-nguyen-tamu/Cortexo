package com.cortexo.lab.models;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface DatasetRepository extends MongoRepository<DatasetRecord, String> {

    Optional<DatasetRecord> findByDatasetIdAndVersion(String datasetId, String version);

    Optional<DatasetRecord> findFirstByDatasetIdOrderByCreatedAtDesc(String datasetId);
}