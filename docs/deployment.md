# Cortexo deployment

All-free deployment topology (blueprint section 79):

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
        +--> lightweight Python service
                |
                +--> tiny scratch model OR replay stored experiment results
```

Heavy experiments run on Kaggle / Colab / local GPU; results are uploaded as
artifacts + metrics + cards into the Cortexo model/experiment registry.

## Cloudflare Pages (section 80)

- Root directory: `apps/web-vue`
- Build: `npm ci && npm run build`
- Output: `dist`
- Env: `VITE_API_BASE_URL=https://YOUR-API-HOST/api`
- Frontend env vars must not contain secrets.
- `infra/cloudflare/_redirects`, `infra/cloudflare/_headers` apply.

## Render Spring Boot (section 81)

Dockerfile: `apps/api-spring/Dockerfile` (Maven multi-stage ->
eclipse-temurin:21-jre, listens on PORT).

Required environment:
`MONGODB_URI`, `POSTGRES_URL`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`ML_GATEWAY_URL`, `FRONTEND_ORIGIN`, `JWT_SECRET`.

Blueprint: `infra/render/render.yaml`. Free web services may sleep; that is
acceptable for a portfolio demo.

## MongoDB Atlas (section 82)

One free cluster; prefer a GCP-backed free region. Holds metadata, registries,
repository snapshots, compact graphs, agent traces, experiment metadata.
Never store huge model weights, huge corpus, or unlimited dense embedding
vectors. If embedding storage grows, keep a compact local index/artifact and
store only metadata.

Schema/index scripts: `infra/mongo/*.js`.

## Python ML service

`ml/src/cortexo_ml/api/main.py` (FastAPI). Uvicorn on port 8000 (or Render).
Heavy-path backends are conditional: without torch/GPU it degrades to the
Echo backend — the platform stays usable fully offline in replay mode.

## Replay mode (section 122)

If no live GPU/model service is available, Cortexo still works:
- load stored experiment output (`artifacts/evaluations/<run-id>/`)
- render token usage, retrieval trace, agent trace, metrics, training curve
- clearly label placeholders: `DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT`,
  and delete placeholder metrics before using numbers anywhere.

## Local start (section 103)

```bash
# Terminal 1 - infra
docker compose -f docker-compose.core.yml up -d

# Terminal 2 - Python
cd ml
python -m venv .venv && source .venv/bin/activate
pip install -e . && pip install -r requirements.txt
uvicorn cortexo_ml.api.main:app --reload --port 8000

# Terminal 3 - Spring (mvn or ./mvnw)
cd apps/api-spring && ./mvnw spring-boot:run

# Terminal 4 - Vue
cd apps/web-vue && npm install && npm run dev
# open http://localhost:5173
# health: http://localhost:8080/api/health  and  http://localhost:8000/health
```

## First API test (section 104)

```bash
curl -X POST http://localhost:8080/api/inference/generate \
  -H "Content-Type: application/json" \
  -d '{"requestId":"demo-1","modelVariantId":"echo-demo","repositorySnapshotId":null,
       "taskId":null,"prompt":"Explain why this test might fail.","seed":42,
       "generation":{"temperature":0.2,"maxNewTokens":128}}'
```

## CI/CD

`.github/workflows/ci.yml`, `ml-tests.yml`, `benchmark-smoke.yml`. Models are
never trained in GitHub Actions; only unit tests, tiny-model smoke, Java tests,
Vue build, migration syntax and benchmark smoke run there.

## Sandbox deployment

`sandbox/` container (non-root, no network, read-only base, bounded
memory/CPU/PID, wall-clock timeout, tmpfs, workspace deleted after run). The
runner (`sandbox/runner.py`) only accepts RESTRICTED command types; free-form
shell is never accepted from the model.