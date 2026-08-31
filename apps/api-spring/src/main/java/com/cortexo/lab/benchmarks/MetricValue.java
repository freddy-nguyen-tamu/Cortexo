package com.cortexo.lab.benchmarks;

import jakarta.persistence.Column;
import jakarta.persistence.FetchType;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "metric_value")
public class MetricValue {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "benchmark_run_id", nullable = false)
    private BenchmarkRun benchmarkRun;

    @Column(name = "metric_name", nullable = false, length = 128)
    private String metricName;

    @Column(name = "metric_value", nullable = false)
    private Double metricValue;

    @Column(length = 64)
    private String unit;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "metadata_json", nullable = false)
    private String metadataJson = "{}";

    protected MetricValue() {
    }

    public MetricValue(BenchmarkRun benchmarkRun, String metricName, Double metricValue,
                       String unit, String metadataJson) {
        this.benchmarkRun = benchmarkRun;
        this.metricName = metricName;
        this.metricValue = metricValue;
        this.unit = unit;
        if (metadataJson != null) {
            this.metadataJson = metadataJson;
        }
    }

    public Long getId() {
        return id;
    }

    public BenchmarkRun getBenchmarkRun() {
        return benchmarkRun;
    }

    public void setBenchmarkRun(BenchmarkRun benchmarkRun) {
        this.benchmarkRun = benchmarkRun;
    }

    public String getMetricName() {
        return metricName;
    }

    public Double getMetricValue() {
        return metricValue;
    }

    public String getUnit() {
        return unit;
    }

    public String getMetadataJson() {
        return metadataJson;
    }
}