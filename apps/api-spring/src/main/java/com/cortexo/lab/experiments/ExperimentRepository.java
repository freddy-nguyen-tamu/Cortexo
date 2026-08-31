package com.cortexo.lab.experiments;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface ExperimentRepository extends MongoRepository<ExperimentRecord, String> {

    Optional<ExperimentRecord> findByExperimentId(String experimentId);

    List<ExperimentRecord> findByStatus(String status);
}