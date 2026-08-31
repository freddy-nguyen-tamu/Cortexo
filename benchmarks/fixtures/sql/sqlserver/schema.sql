-- Microsoft SQL Server schema (PolyDB-SWE fixture)
-- Domain: customer, project, task, invoice, audit_event

IF OBJECT_ID('dbo.audit_event', 'U') IS NOT NULL DROP TABLE dbo.audit_event;
IF OBJECT_ID('dbo.invoice', 'U') IS NOT NULL DROP TABLE dbo.invoice;
IF OBJECT_ID('dbo.task', 'U') IS NOT NULL DROP TABLE dbo.task;
IF OBJECT_ID('dbo.project', 'U') IS NOT NULL DROP TABLE dbo.project;
IF OBJECT_ID('dbo.customer', 'U') IS NOT NULL DROP TABLE dbo.customer;

CREATE TABLE dbo.customer (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    email NVARCHAR(255) NOT NULL UNIQUE,
    created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE dbo.project (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    name NVARCHAR(255) NOT NULL,
    budget_cents BIGINT NOT NULL DEFAULT 0,
    CONSTRAINT fk_project_customer FOREIGN KEY (customer_id) REFERENCES dbo.customer(id)
);

CREATE TABLE dbo.task (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    project_id BIGINT NOT NULL,
    title NVARCHAR(255) NOT NULL,
    status NVARCHAR(32) NOT NULL DEFAULT N'open',
    minutes_spent INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_task_project FOREIGN KEY (project_id) REFERENCES dbo.project(id)
);

CREATE TABLE dbo.invoice (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    project_id BIGINT NOT NULL,
    amount_cents BIGINT NOT NULL,
    issued_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_invoice_project FOREIGN KEY (project_id) REFERENCES dbo.project(id)
);

CREATE TABLE dbo.audit_event (
    id BIGINT IDENTITY(1,1) PRIMARY KEY,
    actor_id BIGINT,
    action NVARCHAR(64) NOT NULL,
    details NVARCHAR(MAX),
    occurred_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE NONCLUSTERED INDEX idx_task_project ON dbo.task(project_id);
CREATE NONCLUSTERED INDEX idx_invoice_project ON dbo.invoice(project_id);