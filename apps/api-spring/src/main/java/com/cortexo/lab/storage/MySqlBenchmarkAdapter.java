package com.cortexo.lab.storage;

import javax.sql.DataSource;
import java.util.List;

public class MySqlBenchmarkAdapter extends AbstractJdbcBenchmarkAdapter {

    private final List<String> tables;

    public MySqlBenchmarkAdapter(DataSource dataSource, boolean enabled, List<String> tables) {
        super(dataSource, enabled, 10, 1000);
        this.tables = tables;
    }

    @Override
    public String id() {
        return "mysql";
    }

    @Override
    public SchemaDescription describeSchema() {
        return new SchemaDescription(id(), "MySQL 8.4", tables);
    }
}