package com.cortexo.lab.benchmarks;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface BenchmarkTaskRepository extends JpaRepository<BenchmarkTask, String> {

    List<BenchmarkTask> findBySuiteId(String suiteId);
}