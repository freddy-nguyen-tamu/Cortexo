import platform
import subprocess
import sys
from pathlib import Path


def git_sha(repo_path: str | Path = ".") -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def git_sha_short(repo_path: str | Path = ".") -> str | None:
    sha = git_sha(repo_path)
    return sha[:12] if sha else None


def git_diff_stat(repo_path: str | Path = ".") -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "diff", "--stat"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def environment_snapshot() -> dict:
    import importlib

    def _ver(name):
        try:
            mod = importlib.import_module(name)
            return getattr(mod, "__version__", "unknown")
        except ImportError:
            return None

    gpu = detect_gpu()
    return {
        "python": platform.python_version(),
        "torch": _ver("torch"),
        "transformers": _ver("transformers"),
        "cuda": _ver("torch.cuda") and (gpu.get("cuda") or None) or None,
        "gpu": gpu.get("name"),
        "cpu": platform.processor() or platform.machine(),
        "ram": gpu.get("ram_mb"),
        "os": platform.system() + " " + platform.release(),
    }


def detect_gpu() -> dict:
    info = {"name": None, "vram_mb": None, "cuda": None, "ram_mb": None}
    try:
        import torch

        info["cuda"] = str(torch.version.cuda) if torch.cuda.is_available() else None
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["name"] = name
            info["vram_mb"] = int(props.total_memory / (1024 * 1024))
    except ImportError:
        pass

    try:
        import psutil

        info["ram_mb"] = int(psutil.virtual_memory().total / (1024 * 1024))
    except ImportError:
        pass
    return info