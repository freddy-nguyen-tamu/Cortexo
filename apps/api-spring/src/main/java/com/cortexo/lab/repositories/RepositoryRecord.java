package com.cortexo.lab.repositories;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;

@Document(collection = "repositories")
public record RepositoryRecord(
        @Id String id,
        String name,
        String url,
        String description,
        String license,
        boolean licenseVerified,
        List<String> languages,
        String ownerUserId,
        String status,
        Instant createdAt) {

    public RepositoryRecord withStatus(String newStatus) {
        return new RepositoryRecord(id, name, url, description, license,
                licenseVerified, languages, ownerUserId, newStatus, createdAt);
    }
}