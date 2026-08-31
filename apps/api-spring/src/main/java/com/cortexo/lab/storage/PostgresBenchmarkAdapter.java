package com.cortexo.lab.storage;

import javax.sql.DataSource;
import java.util.List;

public class PostgresBenchmarkAdapter extends AbstractJdbcBenchmarkAdapter {

    private final List<String> tables;

    public PostgresBenchmarkAdapter(DataSource dataSource, boolean enabled, List<String> tables) {
        super(dataSource, enabled, 10, 1000);
        this.tables = tables;
    }

    @Override
    public String id() {
        return "postgres";
    }

    @Override
    public SchemaDescription describeSchema() {
        return new SchemaDescription(id(), "PostgreSQL", tables);
    }
}