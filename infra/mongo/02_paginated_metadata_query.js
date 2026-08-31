// Paginated metadata query example.
// Returns a page of repository file metadata for a snapshot, newest first.
// Run with:  mongosh mongodb://localhost:27017/cortexo infra/mongo/02_paginated_metadata_query.js snapshotId pageSize
//
// Naming matches the unique compound index {repository, snapshotId, path},
// so a keyset query can also be used for stable pagination on large snapshots.

const snapshotId = args[0] || "snap-demo";
const pageSize = parseInt(args[1] || "50", 10);
const skip = parseInt(args[2] || "0", 10);

const filter = { snapshotId: snapshotId };

const cursor = db.repository_files
  .find(filter, {
    repository: 1,
    path: 1,
    language: 1,
    chunkCount: 1,
    symbolCount: 1,
    lineCount: 1,
  })
  .sort({ path: 1 }) // parallel to the compound index
  .skip(skip)
  .limit(pageSize);

print("page skip=" + skip + " size=" + pageSize);
cursor.forEach((doc) => printjson(doc));

// Keyset variant (preferred for large snapshots):
const lastPath = args[3] || null;
if (lastPath) {
  const keysetFilter = { snapshotId: snapshotId, path: { $gt: lastPath } };
  print("keyset page after path = " + lastPath);
  db.repository_files
    .find(keysetFilter, { repository: 1, path: 1 })
    .sort({ path: 1 })
    .limit(pageSize)
    .forEach((doc) => printjson(doc));
}