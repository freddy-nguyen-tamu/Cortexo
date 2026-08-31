package com.cortexo.lab.benchmarks;

import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface BenchmarkRunRepository extends JpaRepository<BenchmarkRun, String> {

    List<BenchmarkRun> findByTaskId(String taskId);

    List<BenchmarkRun> findByModelVariantId(String modelVariantId);
}