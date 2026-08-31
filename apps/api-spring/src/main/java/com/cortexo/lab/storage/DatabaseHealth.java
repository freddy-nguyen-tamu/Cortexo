package com.cortexo.lab.storage;

public record DatabaseHealth(String id, boolean reachable, long latencyMs, String error) {

    public static DatabaseHealth error(String id) {
        return new DatabaseHealth(id, false, 0, "adapter not found");
    }
}