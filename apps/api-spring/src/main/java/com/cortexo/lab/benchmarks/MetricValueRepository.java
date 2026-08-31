package com.cortexo.lab.benchmarks;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface MetricValueRepository extends JpaRepository<MetricValue, Long> {

    List<MetricValue> findByBenchmarkRunId(String benchmarkRunId);
}