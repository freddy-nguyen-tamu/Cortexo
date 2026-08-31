package com.cortexo.lab.repositories;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.List;

public interface GraphEdgeRepository extends MongoRepository<GraphEdge, String> {

    List<GraphEdge> findBySnapshotId(String snapshotId);
}