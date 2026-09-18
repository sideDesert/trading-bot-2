import os
from pathlib import Path


def load_env_file(path, names=("UPSTOX_ACCESS_TOKEN",)) -> bool:
    wanted = set(names)
    missing = {
        name for name in wanted if not os.environ.get(name, "").strip()
    }
    if not missing:
        return False
    env_path = Path(path)
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    loaded = False
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export "):
            stripped = stripped[len("export ") :].lstrip()
        if "=" not in stripped:
            continue
        name, _, value = stripped.partition("=")
        name = name.strip()
        if name not in missing:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if not value.strip():
            continue
        os.environ[name] = value
        missing.discard(name)
        loaded = True
    return loaded
