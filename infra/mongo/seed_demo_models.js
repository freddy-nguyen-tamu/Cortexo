// Public demo seed for the model registry (blueprint section 107).
// DEMO PLACEHOLDER records are clearly labeled so they are never mistaken
// for real benchmark numbers.
// Run with:  mongosh mongodb://localhost:27017/cortexo infra/mongo/seed_demo_models.js

db.models.deleteMany({ tags: "demo" });

const demoModels = [
  {
    name: "scratch-9m-code",
    modelId: "scratch9m-code-v1",
    family: "scratch",
    technique: "PRETRAIN",
    parentModelId: null,
    parameterCount: 9000000,
    activeParameterCount: 9000000,
    precision: "fp16",
    contextLength: 1024,
    tokenizerId: "code-bpe-16k",
    license: "project-defined",
    artifactUri: "artifacts/models/scratch9m-code-v1/",
    artifactSha256: null,
    tags: ["scratch", "code", "demo"],
    config: { demoSample: true },
    status: "DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT",
    createdAt: new Date()
  },
  {
    name: "scratch-33m-code",
    modelId: "scratch33m-code-v1",
    family: "scratch",
    technique: "PRETRAIN",
    parentModelId: null,
    parameterCount: 33000000,
    activeParameterCount: 33000000,
    precision: "fp16",
    contextLength: 1024,
    tokenizerId: "code-bpe-16k",
    license: "project-defined",
    artifactUri: "artifacts/models/scratch33m-code-v1/",
    artifactSha256: null,
    tags: ["scratch", "code", "demo"],
    config: { demoSample: true },
    status: "DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT",
    createdAt: new Date()
  },
  {
    name: "scratch-70m-code",
    modelId: "scratch70m-code-v1",
    family: "scratch",
    technique: "PRETRAIN",
    parentModelId: null,
    parameterCount: 70000000,
    activeParameterCount: 70000000,
    precision: "fp16",
    contextLength: 1024,
    tokenizerId: "code-bpe-16k",
    license: "project-defined",
    artifactUri: "artifacts/models/scratch70m-code-v1/",
    artifactSha256: null,
    tags: ["scratch", "code", "demo"],
    config: { demoSample: true },
    status: "DEMO PLACEHOLDER - NOT A REAL BENCHMARK RESULT",
    createdAt: new Date()
  },
  {
    name: "Qwen2.5-Coder-0.5B baseline",
    modelId: "qwen05b-base",
    family: "open",
    technique: "BASE",
    parentModelId: null,
    parameterCount: 493000000,
    activeParameterCount: 493000000,
    precision: "fp16",
    contextLength: 32768,
    tokenizerId: "qwen2.5-coder-tokenizer",
    license: "Apache-2.0",
    artifactUri: "hf://Qwen/Qwen2.5-Coder-0.5B",
    artifactSha256: null,
    tags: ["open", "baseline", "demo"],
    config: { hfModelId: "Qwen/Qwen2.5-Coder-0.5B" },
    status: "DEMO PLACEHOLDER - license recorded, weights not downloaded",
    createdAt: new Date()
  }
];

demoModels.forEach((m) => db.models.insertOne(m));
print("seeded " + demoModels.length + " demo model records (labeled placeholders)");