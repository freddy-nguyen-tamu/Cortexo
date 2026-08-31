package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface RepositoryFileRepository extends MongoRepository<RepositoryFile, String> {

    List<RepositoryFile> findBySnapshotId(String snapshotId);

    Optional<RepositoryFile> findBySnapshotIdAndPath(String snapshotId, String path);
}