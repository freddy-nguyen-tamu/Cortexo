package com.cortexo.lab.storage;

import javax.sql.DataSource;
import java.util.List;

public class Db2BenchmarkAdapter extends AbstractJdbcBenchmarkAdapter {

    private final List<String> tables;

    public Db2BenchmarkAdapter(DataSource dataSource, boolean enabled, List<String> tables) {
        super(dataSource, enabled, 10, 1000);
        this.tables = tables;
    }

    @Override
    public String id() {
        return "db2";
    }

    @Override
    public SchemaDescription describeSchema() {
        return new SchemaDescription(id(), "IBM Db2 Community", tables);
    }
}