package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;
import java.util.Optional;

public interface RepositorySymbolRepository extends MongoRepository<RepositorySymbol, String> {

    List<RepositorySymbol> findBySnapshotId(String snapshotId);

    Optional<RepositorySymbol> findBySnapshotIdAndQualifiedName(String snapshotId, String qualifiedName);

    List<RepositorySymbol> findBySnapshotIdAndKind(String snapshotId, String kind);
}