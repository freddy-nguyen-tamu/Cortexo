// Migration example using a cursor (iterate without loading an entire
// collection into memory). Pattern: batched + resumable via a last-seen key.
//
// This example backfills repository_chunks documents with an approximate
// token count when the field is missing, in batches, and logs progress.
// Run with:  mongosh mongodb://localhost:27017/cortexo infra/mongo/03_migration_with_cursor.js

const BATCH_SIZE = 500;

// Use the stable _id as a cursor key when possible; _id is always indexed.
let lastId = null;
let migrated = 0;

while (true) {
  const filter = { tokenCount: { $exists: false } };
  if (lastId !== null) {
    filter._id = { $gt: lastId };
  }

  const batch = db.repository_chunks.find(filter).sort({ _id: 1 }).limit(BATCH_SIZE).toArray();
  if (batch.length === 0) {
    break;
  }

  const ops = batch.map((chunk) => ({
    updateOne: {
      filter: { _id: chunk._id },
      update: { $set: { tokenCount: Math.max(1, Math.round(chunk.text.length / 4)) } },
    },
  }));
  db.repository_chunks.bulkWrite(ops);
  migrated += batch.length;
  lastId = batch[batch.length - 1]._id;

  print("migrated " + migrated + " chunks; lastId=" + lastId);
}

print("migration complete: " + migrated + " chunks backfilled");

// Note: for a large migration prefer the Mongo shell's cursor.iterate() with
// smaller batches, write a progress marker record, and keep the script
// idempotent (the {tokenCount: {$exists:false}} filter makes it so).