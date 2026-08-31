package com.cortexo.lab.storage;

import javax.sql.DataSource;
import java.util.List;

public class SqlServerBenchmarkAdapter extends AbstractJdbcBenchmarkAdapter {

    private final List<String> tables;

    public SqlServerBenchmarkAdapter(DataSource dataSource, boolean enabled, List<String> tables) {
        super(dataSource, enabled, 10, 1000);
        this.tables = tables;
    }

    @Override
    public String id() {
        return "sqlserver";
    }

    @Override
    public SchemaDescription describeSchema() {
        return new SchemaDescription(id(), "Microsoft SQL Server Express", tables);
    }
}