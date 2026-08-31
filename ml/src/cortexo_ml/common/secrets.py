import base64
import re
from dataclasses import dataclass, field
from pathlib import Path

SECRET_PATTERNS = {
    "github_token": re.compile(r"ghp_[A-Za-z0-9]{36}\b"),
    "aws_access_key": re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}\b"),
    "aws_secret_key": re.compile(
        r"(?<![A-Za-z0-9])(?:aws_secret_access_key|secret_access_key)\s*[=:]\s*['\"]?[A-Za-z0-9/+]{40}"
    ),
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"
    ),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "paystack_sk": re.compile(r"sk_(?:live|test)_[A-Za-z0-9]+"),
    "stripe_sk": re.compile(r"sk_(?:live|test)_[A-Za-z0-9]{24,}"),
    "generic_password": re.compile(
        r"(?i)(password|passwd|pwd|secret|api_key|apikey|client_secret)\s*[=:]\s*[^\s'\"]{8,}"
    ),
}


@dataclass
class SecretFinding:
    file: str
    pattern: str
    line: int
    snippet: str


def scan_file(
    path: str | Path,
    patterns: dict[str, re.Pattern] | None = None,
) -> list[SecretFinding]:
    patterns = patterns or SECRET_PATTERNS
    findings: list[SecretFinding] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                for name, pattern in patterns.items():
                    if pattern.search(line):
                        findings.append(
                            SecretFinding(
                                file=str(path),
                                pattern=name,
                                line=lineno,
                                snippet=redact(line.strip(), 120),
                            )
                        )
    except OSError:
        pass
    return findings


def redact(text: str, max_len: int = 120) -> str:
    text = re.sub(
        r"(?i)(password|passwd|pwd|secret|api_key|apikey|client_secret)\s*[=:]\s*\S+",
        r"\1=***REDACTED***",
        text,
    )
    text = re.sub(r"-----BEGIN PRIVATE KEY-----.*", "-----BEGIN PRIVATE KEY-----[REDACTED]", text, flags=re.S)
    return text[:max_len]


def scan_directory(
    root: str | Path,
    patterns: dict[str, re.Pattern] | None = None,
    extensions: set[str] | None = None,
) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        if extensions is not None and path.suffix not in extensions:
            continue
        findings.extend(scan_file(path, patterns))
    return findings


def is_probably_binary(data: bytes) -> bool:
    if b"\x00" in data[:8192]:
        return True
    printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in data[:8192])
    if data:
        return printable / len(data[:8192]) < 0.85
    return False


def encode_private(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def decode_private(value: str) -> str:
    return base64.b64decode(value).decode()


def scrub_env_file(path: str | Path) -> dict[str, str]:
    kept = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, _ = line.partition("=")
        kept[key.strip()] = "***" if "SECRET" in key.upper() or "PASSWORD" in key.upper() else ""
    return kept