package com.cortexo.lab.storage;

import javax.sql.DataSource;
import java.util.List;

public class OracleBenchmarkAdapter extends AbstractJdbcBenchmarkAdapter {

    private final List<String> tables;

    public OracleBenchmarkAdapter(DataSource dataSource, boolean enabled, List<String> tables) {
        super(dataSource, enabled, 10, 1000);
        this.tables = tables;
    }

    @Override
    public String id() {
        return "oracle";
    }

    @Override
    public SchemaDescription describeSchema() {
        return new SchemaDescription(id(), "Oracle AI Database Free", tables);
    }
}