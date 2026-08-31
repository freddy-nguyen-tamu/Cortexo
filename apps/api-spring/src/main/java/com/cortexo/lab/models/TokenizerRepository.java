package com.cortexo.lab.models;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface TokenizerRepository extends MongoRepository<TokenizerRecord, String> {

    Optional<TokenizerRecord> findByTokenizerId(String tokenizerId);
}