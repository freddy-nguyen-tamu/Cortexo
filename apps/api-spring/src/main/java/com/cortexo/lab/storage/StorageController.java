package com.cortexo.lab.storage;

import com.cortexo.lab.common.ApiResponse;
import com.cortexo.lab.storage.cassandra.CassandraTelemetryService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/storage")
public class StorageController {

    private final List<DatabaseBenchmarkAdapter> adapters;
    private final CassandraTelemetryService cassandra;

    public StorageController(List<DatabaseBenchmarkAdapter> adapters,
                             CassandraTelemetryService cassandra) {
        this.adapters = adapters;
        this.cassandra = cassandra;
    }

    @GetMapping("/adapters")
    public ApiResponse<List<Object>> adapters() {
        List<Object> result = new ArrayList<>();
        for (DatabaseBenchmarkAdapter a : adapters) {
            result.add(new AdapterStatus(a.id(), a.enabled(), a.describeSchema(), a.health()));
        }
        result.add(cassandra.status());
        return ApiResponse.ok(result);
    }

    @GetMapping("/adapters/{id}/health")
    public ApiResponse<DatabaseHealth> health(@PathVariable String id) {
        return ApiResponse.ok(adapters.stream()
                .filter(a -> a.id().equalsIgnoreCase(id))
                .findFirst()
                .map(DatabaseBenchmarkAdapter::health)
                .orElse(DatabaseHealth.error(id)));
    }

    public record AdapterStatus(String id, boolean enabled, SchemaDescription schema, DatabaseHealth health) {
    }
}