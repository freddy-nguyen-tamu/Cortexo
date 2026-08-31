package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

public interface RetrievalRunRepository extends MongoRepository<RetrievalRunRecord, String> {
}