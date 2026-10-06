"""Config loading: YAML -> nested attribute-access object, with CLI overrides."""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import yaml

DEFAULT_CONFIG = Path(__file__).with_name("my_config.yaml")


class Config(SimpleNamespace):
    """Nested namespace, e.g. cfg.mil_args.training_args.lr"""

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> dict:
        return {k: _to_plain(v) for k, v in vars(self).items()}


def _to_plain(v: Any) -> Any:
    if isinstance(v, Config):
        return v.to_dict()
    if isinstance(v, list):
        return [_to_plain(x) for x in v]
    return v


def _to_ns(obj: Any) -> Any:
    if isinstance(obj, dict):
        return Config(**{str(k): _to_ns(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_to_ns(v) for v in obj]
    return obj


def _deep_update(base: dict, upd: dict) -> dict:
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
    return base


def parse_overrides(pairs: Iterable[str] | None) -> dict:
    """['mil_args.layer=9', 'main_args.micro_data=true'] -> nested dict (values parsed as YAML)."""
    out: dict = {}
    for pair in pairs or []:
        key, _, raw = pair.partition("=")
        node = out
        parts = key.strip().split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = yaml.safe_load(raw)
    return out


def load_config(path: str | Path | None = None, overrides: dict | None = None) -> Config:
    with open(path or DEFAULT_CONFIG) as f:
        raw = yaml.safe_load(f)
    if overrides:
        raw = _deep_update(copy.deepcopy(raw), overrides)
    return _to_ns(raw)


def cache_path(cfg: Config, *parts: str, mkdir: bool = True) -> Path:
    """Path inside data_args.cache_dir; parent folders are created."""
    p = Path(cfg.data_args.cache_dir).joinpath(*parts)
    if mkdir:
        (p.parent if p.suffix else p).mkdir(parents=True, exist_ok=True)
    return p
