package com.cortexo.lab.auth;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface AppUserRepository extends MongoRepository<AppUser, String> {

    Optional<AppUser> findByUsername(String username);

    Optional<AppUser> findByEmail(String email);
}