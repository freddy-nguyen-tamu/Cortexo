package com.cortexo.lab.storage;

import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.jdbc.DataSourceBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import javax.sql.DataSource;
import java.util.List;

@Configuration
public class DbAdapterConfig {

    public static final List<String> SQL_FIXTURE_TABLES =
            List.of("customer", "project", "task", "invoice", "audit_event");

    @Bean
    @Primary
    @ConfigurationProperties("spring.datasource")
    public DataSourceProperties postgresDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean(name = "dataSource")
    @Primary
    public DataSource postgresDataSource(DataSourceProperties postgresDataSourceProperties) {
        return postgresDataSourceProperties.initializeDataSourceBuilder().build();
    }

    @Bean
    public PostgresBenchmarkAdapter postgresBenchmarkAdapter(DataSource dataSource) {
        return new PostgresBenchmarkAdapter(dataSource, true,
                List.of("benchmark_suite", "benchmark_task", "benchmark_run", "metric_value"));
    }

    @Bean(name = "mysqlDataSource")
    @ConditionalOnProperty(name = "mysql.enabled", havingValue = "true")
    public DataSource mysqlDataSource(
            @Value("${MYSQL_URL:jdbc:mysql://localhost:3306/cortexo_mysql}") String url,
            @Value("${MYSQL_USER:cortexo}") String user,
            @Value("${MYSQL_PASSWORD:cortexo}") String password) {
        return build("com.mysql.cj.jdbc.Driver", url, user, password);
    }

    @Bean(name = "sqlserverDataSource")
    @ConditionalOnProperty(name = "sqlserver.enabled", havingValue = "true")
    public DataSource sqlserverDataSource(
            @Value("${SQLSERVER_URL:jdbc:sqlserver://localhost:1433;databaseName=cortexo;encrypt=false}") String url,
            @Value("${SQLSERVER_USER:sa}") String user,
            @Value("${SQLSERVER_PASSWORD:ChangeThisStrongPassword123!}") String password) {
        return build("com.microsoft.sqlserver.jdbc.SQLServerDriver", url, user, password);
    }

    @Bean(name = "oracleDataSource")
    @ConditionalOnProperty(name = "oracle.enabled", havingValue = "true")
    public DataSource oracleDataSource(
            @Value("${ORACLE_URL:jdbc:oracle:thin:@localhost:1521/FREEPDB1}") String url,
            @Value("${ORACLE_USER:app}") String user,
            @Value("${ORACLE_PASSWORD:app}") String password) {
        return build("oracle.jdbc.OracleDriver", url, user, password);
    }

    @Bean(name = "db2DataSource")
    @ConditionalOnProperty(name = "db2.enabled", havingValue = "true")
    public DataSource db2DataSource(
            @Value("${DB2_URL:jdbc:db2://localhost:50000/cortexo}") String url,
            @Value("${DB2_USER:db2inst1}") String user,
            @Value("${DB2_PASSWORD:ChangeThisStrongPassword123!}") String password) {
        return build("com.ibm.db2.jcc.DB2Driver", url, user, password);
    }

    @Bean
    @ConditionalOnProperty(name = "mysql.enabled", havingValue = "true")
    public MySqlBenchmarkAdapter mySqlBenchmarkAdapter(@org.springframework.beans.factory.annotation.Qualifier("mysqlDataSource") DataSource dataSource) {
        return new MySqlBenchmarkAdapter(dataSource, true, SQL_FIXTURE_TABLES);
    }

    @Bean
    @ConditionalOnProperty(name = "sqlserver.enabled", havingValue = "true")
    public SqlServerBenchmarkAdapter sqlServerBenchmarkAdapter(@org.springframework.beans.factory.annotation.Qualifier("sqlserverDataSource") DataSource dataSource) {
        return new SqlServerBenchmarkAdapter(dataSource, true, SQL_FIXTURE_TABLES);
    }

    @Bean
    @ConditionalOnProperty(name = "oracle.enabled", havingValue = "true")
    public OracleBenchmarkAdapter oracleBenchmarkAdapter(@org.springframework.beans.factory.annotation.Qualifier("oracleDataSource") DataSource dataSource) {
        return new OracleBenchmarkAdapter(dataSource, true, SQL_FIXTURE_TABLES);
    }

    @Bean
    @ConditionalOnProperty(name = "db2.enabled", havingValue = "true")
    public Db2BenchmarkAdapter db2BenchmarkAdapter(@org.springframework.beans.factory.annotation.Qualifier("db2DataSource") DataSource dataSource) {
        return new Db2BenchmarkAdapter(dataSource, true, SQL_FIXTURE_TABLES);
    }

    private static DataSource build(String driverClassName, String url, String user, String password) {
        return DataSourceBuilder.create()
                .driverClassName(driverClassName)
                .url(url)
                .username(user)
                .password(password)
                .build();
    }
}