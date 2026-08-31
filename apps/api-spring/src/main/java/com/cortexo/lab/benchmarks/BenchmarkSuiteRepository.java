package com.cortexo.lab.benchmarks;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface BenchmarkSuiteRepository extends JpaRepository<BenchmarkSuite, String> {

    List<BenchmarkSuite> findByName(String name);
}