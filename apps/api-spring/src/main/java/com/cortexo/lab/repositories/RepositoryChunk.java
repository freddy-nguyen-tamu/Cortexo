package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "repository_chunks")
public record RepositoryChunk(
        @Id String id,
        String snapshotId,
        String fileId,
        String symbolId,
        String kind,
        String content,
        int tokens) {
}