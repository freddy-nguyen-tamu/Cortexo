-- IBM Db2 schema (PolyDB-SWE fixture)
-- Domain: customer, project, task, invoice, audit_event
-- Note: Db2 requires statement terminators; no `CREATE TABLE IF NOT EXISTS`.

CREATE TABLE customer (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    budget_cents BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_project_customer FOREIGN KEY (customer_id) REFERENCES customer(id)
);

CREATE TABLE task (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    minutes_spent INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_task_project FOREIGN KEY (project_id) REFERENCES project(id)
);

CREATE TABLE invoice (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL,
    amount_cents BIGINT NOT NULL,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoice_project FOREIGN KEY (project_id) REFERENCES project(id)
);

CREATE TABLE audit_event (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id BIGINT,
    action VARCHAR(64) NOT NULL,
    details CLOB,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_task_project ON task(project_id);
CREATE INDEX idx_invoice_project ON invoice(project_id);