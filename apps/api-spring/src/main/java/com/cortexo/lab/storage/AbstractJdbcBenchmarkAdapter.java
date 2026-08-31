package com.cortexo.lab.storage;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

public abstract class AbstractJdbcBenchmarkAdapter implements DatabaseBenchmarkAdapter {

    private static final Logger log = LoggerFactory.getLogger(AbstractJdbcBenchmarkAdapter.class);

    protected final DataSource dataSource;
    protected final boolean enabled;
    protected final int timeoutSeconds;
    protected final int maxRows;

    protected AbstractJdbcBenchmarkAdapter(DataSource dataSource, boolean enabled,
                                           int timeoutSeconds, int maxRows) {
        this.dataSource = dataSource;
        this.enabled = enabled;
        this.timeoutSeconds = timeoutSeconds;
        this.maxRows = maxRows;
    }

    @Override
    public boolean enabled() {
        return enabled;
    }

    @Override
    public DatabaseHealth health() {
        if (!enabled) {
            return new DatabaseHealth(id(), false, 0, "disabled");
        }
        long start = System.currentTimeMillis();
        try {
            String firstColumn = executeReadOnly("SELECT 1").columns().get(0);
            return new DatabaseHealth(id(), true, System.currentTimeMillis() - start, null);
        } catch (Exception e) {
            return new DatabaseHealth(id(), false, System.currentTimeMillis() - start, e.getMessage());
        }
    }

    @Override
    public QueryResult executeReadOnly(String sql) {
        if (!enabled) {
            return QueryResult.error("adapter disabled");
        }
        String statement = sql.trim();
        if (statement.isEmpty()) {
            return QueryResult.error("empty statement");
        }
        if (!statement.regionMatches(true, 0, "select", 0, 6)) {
            return QueryResult.error("read-only adapter allows only SELECT statements");
        }

        try (Connection connection = dataSource.getConnection();
             PreparedStatement ps = connection.prepareStatement(statement)) {
            ps.setQueryTimeout(timeoutSeconds);
            ps.setMaxRows(maxRows);
            try (ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData meta = rs.getMetaData();
                int columnCount = meta.getColumnCount();
                List<String> columns = new ArrayList<>();
                for (int i = 1; i <= columnCount; i++) {
                    columns.add(meta.getColumnLabel(i));
                }
                List<List<Object>> rows = new ArrayList<>();
                while (rs.next()) {
                    List<Object> row = new ArrayList<>();
                    for (int i = 1; i <= columnCount; i++) {
                        row.add(rs.getObject(i));
                    }
                    rows.add(row);
                }
                return new QueryResult(columns, rows, null);
            }
        } catch (SQLException e) {
            log.warn("database adapter query failed id={} error={}", id(), e.getMessage());
            return QueryResult.error(e.getMessage());
        }
    }

    @Override
    public void resetFixture() {
        throw new UnsupportedOperationException("fixture reset not implemented for " + id());
    }
}