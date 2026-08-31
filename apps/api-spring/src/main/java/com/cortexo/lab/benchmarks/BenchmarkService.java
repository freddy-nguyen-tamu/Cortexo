package com.cortexo.lab.benchmarks;

import com.cortexo.lab.common.ApiException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Service
public class BenchmarkService {

    private final BenchmarkSuiteRepository suites;
    private final BenchmarkTaskRepository tasks;
    private final BenchmarkRunRepository runs;
    private final MetricValueRepository metrics;

    public BenchmarkService(BenchmarkSuiteRepository suites,
                            BenchmarkTaskRepository tasks,
                            BenchmarkRunRepository runs,
                            MetricValueRepository metrics) {
        this.suites = suites;
        this.tasks = tasks;
        this.runs = runs;
        this.metrics = metrics;
    }

    public BenchmarkSuite registerSuite(String id, String name, String version) {
        return suites.save(new BenchmarkSuite(id, name, version, Instant.now()));
    }

    public BenchmarkTask addTask(String id, String suiteId, String taskType, String repositorySnapshotId,
                                 String difficulty, String metadataJson) {
        BenchmarkSuite suite = suites.findById(suiteId)
                .orElseThrow(() -> ApiException.notFound("suite not found: " + suiteId));
        return tasks.save(new BenchmarkTask(id, suite, taskType, repositorySnapshotId,
                difficulty, metadataJson));
    }

    public BenchmarkRun startRun(String id, String taskId, String modelVariantId, String experimentId, int seed) {
        BenchmarkTask task = tasks.findById(taskId)
                .orElseThrow(() -> ApiException.notFound("task not found: " + taskId));
        return runs.save(new BenchmarkRun(id, task, modelVariantId, experimentId, seed,
                "RUNNING", Instant.now(), null));
    }

    @Transactional
    public BenchmarkRun finishRun(String runId, String status, List<MetricValue> metricValues) {
        BenchmarkRun run = runs.findById(runId)
                .orElseThrow(() -> ApiException.notFound("run not found: " + runId));
        run.setStatus(status);
        run.setFinishedAt(Instant.now());
        runs.save(run);
        for (MetricValue m : metricValues) {
            metrics.save(new MetricValue(run, m.getMetricName(), m.getMetricValue(),
                    m.getUnit(), m.getMetadataJson()));
        }
        return run;
    }

    public List<BenchmarkSuite> listSuites() {
        return suites.findAll();
    }

    public List<BenchmarkTask> tasksOfSuite(String suiteId) {
        return tasks.findBySuiteId(suiteId);
    }

    public List<BenchmarkRun> runsOfModel(String modelVariantId) {
        return runs.findByModelVariantId(modelVariantId);
    }
}