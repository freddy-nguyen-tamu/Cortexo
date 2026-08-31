from pathlib import Path

dirs = '''
apps/web-vue/src/router
apps/web-vue/src/api
apps/web-vue/src/types
apps/web-vue/src/stores
apps/web-vue/src/views
apps/web-vue/src/components/common
apps/web-vue/src/components/visualizers
apps/api-spring/src/main/java/com/cortexo/lab/config
apps/api-spring/src/main/java/com/cortexo/lab/common
apps/api-spring/src/main/java/com/cortexo/lab/auth
apps/api-spring/src/main/java/com/cortexo/lab/repositories
apps/api-spring/src/main/java/com/cortexo/lab/models
apps/api-spring/src/main/java/com/cortexo/lab/experiments
apps/api-spring/src/main/java/com/cortexo/lab/benchmarks
apps/api-spring/src/main/java/com/cortexo/lab/inference
apps/api-spring/src/main/java/com/cortexo/lab/agents
apps/api-spring/src/main/java/com/cortexo/lab/storage/redis
apps/api-spring/src/main/java/com/cortexo/lab/storage/mysql
apps/api-spring/src/main/java/com/cortexo/lab/storage/sqlserver
apps/api-spring/src/main/java/com/cortexo/lab/storage/oracle
apps/api-spring/src/main/java/com/cortexo/lab/storage/db2
apps/api-spring/src/main/java/com/cortexo/lab/storage/cassandra
apps/api-spring/src/main/resources/db/migration
apps/api-spring/src/main/resources/mapper
apps/api-spring/src/test/java/com/cortexo/lab
ml/src/cortexo_ml/api
ml/src/cortexo_ml/common
ml/src/cortexo_ml/tokenization
ml/src/cortexo_ml/scratch_model
ml/src/cortexo_ml/training/configs
ml/src/cortexo_ml/post_training
ml/src/cortexo_ml/data
ml/src/cortexo_ml/repository
ml/src/cortexo_ml/retrieval
ml/src/cortexo_ml/graph
ml/src/cortexo_ml/agents
ml/src/cortexo_ml/routing
ml/src/cortexo_ml/serving
ml/src/cortexo_ml/evaluation
ml/src/cortexo_ml/observability
ml/src/cortexo_ml/visualization
ml/tests
datasets/manifests
datasets/raw
datasets/interim
datasets/processed
datasets/benchmark
artifacts/tokenizers
artifacts/models
artifacts/adapters
artifacts/quantized
artifacts/evaluations
artifacts/visualizations
benchmarks/fixtures
benchmarks/tasks
benchmarks/hidden_tests
benchmarks/suites
notebooks/kaggle
notebooks/colab
notebooks/databricks
sandbox
scripts
infra/cloudflare
infra/render
infra/mongodb
infra/postgres
infra/research-db/init
docs
.github/workflows
'''.strip().splitlines()

for d in dirs:
    Path(d).mkdir(parents=True, exist_ok=True)

print(f"created {len(dirs)} directories")