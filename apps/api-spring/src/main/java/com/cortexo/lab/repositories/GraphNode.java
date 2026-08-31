package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "repository_graph_nodes")
public record GraphNode(
        @Id String id,
        String snapshotId,
        String entityId,
        String kind,
        String name,
        String qualifiedName,
        String path) {
}