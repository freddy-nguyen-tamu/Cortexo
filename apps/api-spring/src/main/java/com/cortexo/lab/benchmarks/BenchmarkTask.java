package com.cortexo.lab.benchmarks;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "benchmark_task")
public class BenchmarkTask {

    @Id
    @Column(length = 128)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "suite_id", nullable = false)
    private BenchmarkSuite suite;

    @Column(name = "task_type", nullable = false, length = 64)
    private String taskType;

    @Column(name = "repository_snapshot_id", length = 128)
    private String repositorySnapshotId;

    @Column(length = 32)
    private String difficulty;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false)
    private String metadataJson = "{}";

    protected BenchmarkTask() {
    }

    public BenchmarkTask(String id, BenchmarkSuite suite, String taskType,
                         String repositorySnapshotId, String difficulty, String metadataJson) {
        this.id = id;
        this.suite = suite;
        this.taskType = taskType;
        this.repositorySnapshotId = repositorySnapshotId;
        this.difficulty = difficulty;
        if (metadataJson != null) {
            this.metadataJson = metadataJson;
        }
    }

    public String getId() {
        return id;
    }

    public BenchmarkSuite getSuite() {
        return suite;
    }

    public void setSuite(BenchmarkSuite suite) {
        this.suite = suite;
    }

    public String getTaskType() {
        return taskType;
    }

    public String getRepositorySnapshotId() {
        return repositorySnapshotId;
    }

    public String getDifficulty() {
        return difficulty;
    }

    public String getMetadataJson() {
        return metadataJson;
    }
}