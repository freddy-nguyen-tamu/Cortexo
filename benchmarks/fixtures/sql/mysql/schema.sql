-- MySQL schema (PolyDB-SWE fixture, MySQL 8.x)
-- Domain: customer, project, task, invoice, audit_event

CREATE TABLE IF NOT EXISTS customer (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS project (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    name VARCHAR(255) NOT NULL,
    budget_cents BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_project_customer FOREIGN KEY (customer_id) REFERENCES customer(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    minutes_spent INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_task_project FOREIGN KEY (project_id) REFERENCES project(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS invoice (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    project_id BIGINT NOT NULL,
    amount_cents BIGINT NOT NULL,
    issued_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invoice_project FOREIGN KEY (project_id) REFERENCES project(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS audit_event (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    actor_id BIGINT,
    action VARCHAR(64) NOT NULL,
    details JSON,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_task_project ON task(project_id);
CREATE INDEX idx_invoice_project ON invoice(project_id);