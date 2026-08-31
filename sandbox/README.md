# Cortexo Execution Sandbox

Sandboxes generated code. Generated code is **untrusted**.

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Immutable base image with Python/Java/Node toolchains |
| `policy.py` | Request validation, predefined command map, resource limits |
| `runner.py` | Launches a disposable container and streams back results |
| `seccomp-profile.json` | Additional syscall restriction profile (network syscalls denied) |

## Invariants

The model **never** supplies a free-form shell command. The runner maps a
restricted `commandType` + `language` to one predefined command:

- `commandType` ∈ `TEST`, `COMPILE`, `LINT`, `FORMAT`, `STATIC_ANALYSIS`
- `language` ∈ `python`, `java`, `javascript`, `typescript`, `shell`, ...

Every container runs with:

```
--rm --network none --memory 1g --cpus 1 --pids-limit 128 --read-only
--tmpfs /tmp:rw,noexec,nosuid,size=256m --user 10001:10001
--cap-drop ALL --security-opt no-new-privileges:true
--security-opt seccomp=sandbox/seccomp-profile.json
```

Wall-clock timeout (`timeout --kill-after` inside + Docker pid file kill on the
host), process-tree kill, read-only base FS, disposable workspace. The
workspace directory is deleted after each run unless `--keep-workspace`.

Never done: executing on the Spring host, mounting the Docker socket, host
credentials, default internet access, root user, arbitrary host mounts.

## Quick start

```bash
# build the image once
docker build -t cortexo-sandbox:latest sandbox

# build the image and run a test request
mkdir -p /tmp/sandbox-demo-ws && cp -r benchmarks/fixtures/repos/python-inventory/* /tmp/sandbox-demo-ws/

cat > /tmp/req.json <<'JSON'
{"workspaceId": "demo-ws", "commandType": "TEST", "language": "python", "timeoutSeconds": 60}
JSON

python3 sandbox/runner.py --request-file /tmp/req.json --workspace /tmp/sandbox-demo-ws
```

The response follows the Python `Verifier` contract:

```json
{
  "ok": true, "passed": false, "policy": false,
  "exitCode": 1, "stdout": "...", "stderr": "...", "timedOut": false,
  "durationMs": 1234, "commandType": "python3"
}
```

`Verifier` in `ml/src/cortexo_ml/agents/verifier.py` maps failures to
`SANDBOX_TIMEOUT` / `SANDBOX_POLICY` / `COMPILE_FAIL` / `TEST_FAIL` / `TOOL_ERROR`.

## Security notes

- The strict seccomp profile denies network-family syscalls on top of
  `--network none` (defense in depth). If a toolchain needs a syscall you
  believe is safe, review the Docker seccomp reference before adding it.
- `policy.check_generated_patch` flags suspicious literals in generated
  patches (base64, /etc/shadow, curl/wget, chmod 777). It is an advisory
  filter, not a substitute for the sandbox.
- Journaling: failures are tagged `SANDBOX_TIMEOUT` / `SANDBOX_POLICY` and
  surface in the dashboard by model and task type.

## Tuning

`CORTEXO_SANDBOX_IMAGE` overrides the image name. Resource defaults live in
`policy.py` (`DEFAULT_MEMORY=1g`, `DEFAULT_CPUS=1`, `DEFAULT_PIDS=128`,
`MAX_TIMEOUT_SECONDS=300`).