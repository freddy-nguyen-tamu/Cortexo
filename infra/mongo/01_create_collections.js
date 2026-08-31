// Cortexo MongoDB schema bootstrap.
// Run with:  mongosh mongodb://localhost:27017/cortexo infra/mongo/01_create_collections.js

const dbName = "cortexo";
use(dbName);

const collections = [
  "users",
  "repositories",
  "repository_snapshots",
  "repository_files",
  "repository_symbols",
  "repository_chunks",
  "repository_graph_nodes",
  "repository_graph_edges",
  "models",
  "tokenizers",
  "datasets",
  "training_runs",
  "experiments",
  "agent_runs",
  "retrieval_runs",
  "router_decisions"
];

collections.forEach((name) => {
  db.createCollection(name);
});

// Unique compound index: one path per snapshot per repository.
// Applies to files and chunks (chunk ids already include the path).
db.repository_files.createIndex(
  { repository: 1, snapshotId: 1, path: 1 },
  { unique: true, name: "uniq_repo_snapshot_path" }
);
db.repository_chunks.createIndex(
  { repository: 1, snapshotId: 1, path: 1 },
  { name: "idx_repo_snapshot_path" }
);
db.repository_chunks.createIndex({ snapshotId: 1 });
db.repository_symbols.createIndex({ repository: 1, snapshotId: 1, name: 1 });
db.repository_symbols.createIndex({ snapshotId: 1, kind: 1 });
db.repository_graph_edges.createIndex({ repository: 1, snapshotId: 1, source: 1 });
db.repository_graph_edges.createIndex({ repository: 1, snapshotId: 1, edgeType: 1 });
db.models.createIndex({ family: 1, technique: 1 });
db.models.createIndex({ parentModelId: 1 });
db.experiments.createIndex({ modelVariantId: 1, createdAt: -1 });
db.experiments.createIndex({ taskId: 1 });
db.agent_runs.createIndex({ runId: 1 }, { unique: true });
db.retrieval_runs.createIndex({ snapshotId: 1, createdAt: -1 });
db.router_decisions.createIndex({ modelVariantId: 1, createdAt: -1 });
db.tokenizers.createIndex({ tokenizerId: 1 }, { unique: true });
db.datasets.createIndex({ datasetId: 1 }, { unique: true });

print("cortexo schema ready on db:", dbName);