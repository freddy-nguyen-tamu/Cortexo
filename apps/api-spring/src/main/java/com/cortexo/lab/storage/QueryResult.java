package com.cortexo.lab.storage;

import java.util.List;

public record QueryResult(List<String> columns, List<List<Object>> rows, String error) {

    public static QueryResult error(String message) {
        return new QueryResult(List.of(), List.of(), message);
    }
}