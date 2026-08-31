# Cortexo infrastructure

Everything needed to run, migrate and deploy Cortexo's data plane.

## Layout

```
infra/
|-- cloudflare/        Cloudflare Pages config (_redirects, _headers, build notes)
|-- render/            Render blueprint for the Spring Boot API
|-- mongodb/           MongoDB schema + index + migration + demo-seed scripts
|-- postgres/          PostgreSQL normalized evaluation schema
|-- research-db/       Offline multi-database research environment notes
```

## MongoDB

```bash
mongosh mongodb://localhost:27017/cortexo infra/mongo/01_create_collections.js
mongosh mongodb://localhost:27017/cortexo infra/mongo/02_paginated_metadata_query.js snap-demo 50 0
mongosh mongodb://localhost:27017/cortexo infra/mongo/03_migration_with_cursor.js
mongosh mongodb://localhost:27017/cortexo infra/mongo/seed_demo_models.js
```

Key points:
- Unique compound index `{repository, snapshotId, path}` guards one path per
  snapshot per repository.
- Keyset pagination example matches the index order for large snapshots.
- The migration script is batched + resumable + idempotent.
- Model records seeded by `seed_demo_models.js` carry the literal label
  `DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT`.

## PostgreSQL

The app owns its schema through Flyway
(`apps/api-spring/src/main/resources/db/migration/V1__benchmark_schema.sql`).
`infra/postgres/eval_schema.sql` mirror is for manual/local setups.

## Deployment topology (blueprint 79)

```
Cloudflare Pages (Vue)
        |
        v
Render Spring Boot
        |
        +--> MongoDB Atlas Free
        |
        +--> optional Neon PostgreSQL Free
        |
        +--> optional Redis-compatible free cache
        |
        +--> lightweight Python service (tiny model or replay mode)
```

Heavy training happens on Kaggle/Colab/local GPU; results land in the Cortexo
model/experiment registry as artifacts + metrics + cards.