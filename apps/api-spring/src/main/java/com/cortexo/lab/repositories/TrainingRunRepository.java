package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface TrainingRunRepository extends MongoRepository<TrainingRunRecord, String> {

    Optional<TrainingRunRecord> findByRunId(String runId);

    List<TrainingRunRecord> findByModelVariantId(String modelVariantId);
}