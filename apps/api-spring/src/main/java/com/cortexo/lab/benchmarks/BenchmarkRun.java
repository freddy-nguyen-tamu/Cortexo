package com.cortexo.lab.benchmarks;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

import java.time.Instant;

@Entity
@Table(name = "benchmark_run")
public class BenchmarkRun {

    @Id
    @Column(length = 128)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "task_id", nullable = false)
    private BenchmarkTask task;

    @Column(name = "model_variant_id", nullable = false, length = 128)
    private String modelVariantId;

    @Column(name = "experiment_id", length = 128)
    private String experimentId;

    @Column(nullable = false)
    private Integer seed;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(name = "started_at")
    private Instant startedAt;

    @Column(name = "finished_at")
    private Instant finishedAt;

    protected BenchmarkRun() {
    }

    public BenchmarkRun(String id, BenchmarkTask task, String modelVariantId, String experimentId,
                        Integer seed, String status, Instant startedAt, Instant finishedAt) {
        this.id = id;
        this.task = task;
        this.modelVariantId = modelVariantId;
        this.experimentId = experimentId;
        this.seed = seed;
        this.status = status;
        this.startedAt = startedAt;
        this.finishedAt = finishedAt;
    }

    public String getId() {
        return id;
    }

    public BenchmarkTask getTask() {
        return task;
    }

    public void setTask(BenchmarkTask task) {
        this.task = task;
    }

    public String getModelVariantId() {
        return modelVariantId;
    }

    public String getExperimentId() {
        return experimentId;
    }

    public Integer getSeed() {
        return seed;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Instant getStartedAt() {
        return startedAt;
    }

    public void setStartedAt(Instant startedAt) {
        this.startedAt = startedAt;
    }

    public Instant getFinishedAt() {
        return finishedAt;
    }

    public void setFinishedAt(Instant finishedAt) {
        this.finishedAt = finishedAt;
    }
}