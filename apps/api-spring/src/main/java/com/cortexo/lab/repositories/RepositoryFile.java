package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "repository_files")
public record RepositoryFile(
        @Id String id,
        String snapshotId,
        String path,
        String language,
        long sizeBytes,
        String sha256) {
}