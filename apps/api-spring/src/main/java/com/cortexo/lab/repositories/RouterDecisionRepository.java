package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

public interface RouterDecisionRepository extends MongoRepository<RouterDecisionRecord, String> {
}