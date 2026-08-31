package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface RepositoryChunkRepository extends MongoRepository<RepositoryChunk, String> {

    List<RepositoryChunk> findBySnapshotId(String snapshotId);
}