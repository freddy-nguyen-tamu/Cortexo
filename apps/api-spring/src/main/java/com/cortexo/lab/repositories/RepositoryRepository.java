package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface RepositoryRepository extends MongoRepository<RepositoryRecord, String> {

    Optional<RepositoryRecord> findByName(String name);
}