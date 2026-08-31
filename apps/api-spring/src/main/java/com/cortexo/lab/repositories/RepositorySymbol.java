package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document(collection = "repository_symbols")
public record RepositorySymbol(
        @Id String id,
        String snapshotId,
        String fileId,
        String kind,
        String name,
        String qualifiedName,
        int line,
        int column,
        int endLine,
        int endColumn,
        String signature) {
}