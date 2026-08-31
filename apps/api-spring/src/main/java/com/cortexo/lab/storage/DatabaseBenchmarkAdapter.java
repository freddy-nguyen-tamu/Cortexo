package com.cortexo.lab.storage;

public interface DatabaseBenchmarkAdapter {

    String id();

    boolean enabled();

    DatabaseHealth health();

    SchemaDescription describeSchema();

    QueryResult executeReadOnly(String sql);

    void resetFixture();
}