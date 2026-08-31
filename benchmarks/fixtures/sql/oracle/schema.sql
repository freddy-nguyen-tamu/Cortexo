-- Oracle schema (PolyDB-SWE fixture, Oracle 23ai "AI Database")
-- Domain: customer, project, task, invoice, audit_event
-- Note: Oracle 23ai allows the standard BOOLEAN type; older releases do not.

CREATE TABLE customer (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(255) NOT NULL,
    email VARCHAR2(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE project (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id NUMBER NOT NULL CONSTRAINT fk_project_customer REFERENCES customer(id),
    name VARCHAR2(255) NOT NULL,
    budget_cents NUMBER(18) DEFAULT 0 NOT NULL
);

CREATE TABLE task (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id NUMBER NOT NULL CONSTRAINT fk_task_project REFERENCES project(id),
    title VARCHAR2(255) NOT NULL,
    status VARCHAR2(32) DEFAULT 'open' NOT NULL,
    minutes_spent NUMBER(10) DEFAULT 0 NOT NULL
);

CREATE TABLE invoice (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id NUMBER NOT NULL CONSTRAINT fk_invoice_project REFERENCES project(id),
    amount_cents NUMBER(18) NOT NULL,
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE TABLE audit_event (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_id NUMBER,
    action VARCHAR2(64) NOT NULL,
    details CLOB,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE INDEX idx_task_project ON task(project_id);
CREATE INDEX idx_invoice_project ON invoice(project_id);