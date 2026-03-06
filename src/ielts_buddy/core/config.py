"""TOML 配置管理

配置文件位于 ~/.ielts-buddy/config.toml，首次运行时自动创建。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Python 3.11+ 内置 tomllib，3.10 需要 fallback
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


# 默认配置
DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "daily_count": 50,
        "default_band": 7,
    },
}

# 应用数据目录
APP_DIR = Path(os.environ.get("IELTS_BUDDY_HOME", "~/.ielts-buddy")).expanduser()
CONFIG_PATH = APP_DIR / "config.toml"
DB_PATH = APP_DIR / "data.db"


def _serialize_toml(data: dict[str, Any]) -> str:
    """将字典序列化为 TOML 格式字符串（简易实现，避免额外依赖）"""
    lines: list[str] = []
    # 先写非 table 值
    for key, value in data.items():
        if not isinstance(value, dict):
            lines.append(f"{key} = {_toml_value(value)}")
    # 再写 table
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"\n[{key}]")
            for k, v in value.items():
                lines.append(f"{k} = {_toml_value(v)}")
    return "\n".join(lines) + "\n"


def _toml_value(value: Any) -> str:
    """将 Python 值转换为 TOML 值字符串"""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        items = ", ".join(_toml_value(v) for v in value)
        return f"[{items}]"
    return f'"{value}"'


class Config:
    """TOML 配置管理器"""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self.path = Path(config_path).expanduser() if config_path else CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """加载配置文件，不存在则使用默认值"""
        if self.path.exists() and tomllib is not None:
            with open(self.path, "rb") as f:
                self._data = tomllib.load(f)
        else:
            self._data = {k: dict(v) if isinstance(v, dict) else v for k, v in DEFAULT_CONFIG.items()}

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项，支持 'section.key' 格式的点分路径"""
        parts = key.split(".")
        obj: Any = self._data
        for part in parts:
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                return default
            if obj is None:
                return default
        return obj

    def set(self, key: str, value: Any) -> None:
        """设置配置项，支持 'section.key' 格式的点分路径"""
        parts = key.split(".")
        obj = self._data
        for part in parts[:-1]:
            if part not in obj or not isinstance(obj[part], dict):
                obj[part] = {}
            obj = obj[part]
        obj[parts[-1]] = value

    def save(self) -> None:
        """保存配置到文件"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(_serialize_toml(self._data), encoding="utf-8")

    def ensure_app_dir(self) -> Path:
        """确保应用数据目录存在并返回路径"""
        app_dir = self.path.parent
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir
