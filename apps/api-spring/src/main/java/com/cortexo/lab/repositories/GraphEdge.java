package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "repository_graph_edges")
public record GraphEdge(
        @Id String id,
        String snapshotId,
        String sourceId,
        String targetId,
        String kind) {
}