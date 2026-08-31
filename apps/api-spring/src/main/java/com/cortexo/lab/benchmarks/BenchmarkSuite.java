package com.cortexo.lab.benchmarks;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "benchmark_suite")
public class BenchmarkSuite {

    @Id
    @Column(length = 128)
    private String id;

    @Column(nullable = false, length = 255)
    private String name;

    @Column(nullable = false, length = 64)
    private String version;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    protected BenchmarkSuite() {
    }

    public BenchmarkSuite(String id, String name, String version, Instant createdAt) {
        this.id = id;
        this.name = name;
        this.version = version;
        this.createdAt = createdAt;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getVersion() {
        return version;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }
}