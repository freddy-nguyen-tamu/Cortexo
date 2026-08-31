package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface RepositorySnapshotRepository extends MongoRepository<RepositorySnapshot, String> {

    List<RepositorySnapshot> findByRepositoryId(String repositoryId);

    Optional<RepositorySnapshot> findFirstByRepositoryIdOrderByCreatedAtDesc(String repositoryId);
}