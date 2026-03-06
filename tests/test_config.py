"""测试配置管理"""

from __future__ import annotations

from pathlib import Path

import pytest

from ielts_buddy.core.config import Config, DEFAULT_CONFIG, _serialize_toml, _toml_value


class TestTomlValue:
    """测试 TOML 值序列化"""

    def test_bool_true(self):
        assert _toml_value(True) == "true"

    def test_bool_false(self):
        assert _toml_value(False) == "false"

    def test_int(self):
        assert _toml_value(42) == "42"

    def test_float(self):
        assert _toml_value(3.14) == "3.14"

    def test_str(self):
        assert _toml_value("hello") == '"hello"'

    def test_list(self):
        result = _toml_value([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_list_of_strings(self):
        result = _toml_value(["a", "b"])
        assert result == '["a", "b"]'

    def test_empty_list(self):
        assert _toml_value([]) == "[]"


class TestSerializeToml:
    """测试 TOML 序列化"""

    def test_simple_dict(self):
        data = {"general": {"daily_count": 50, "default_band": 7}}
        result = _serialize_toml(data)
        assert "[general]" in result
        assert "daily_count = 50" in result
        assert "default_band = 7" in result

    def test_mixed_data(self):
        data = {"version": 1, "section": {"key": "value"}}
        result = _serialize_toml(data)
        assert "version = 1" in result
        assert "[section]" in result
        assert 'key = "value"' in result


class TestConfig:
    """测试配置管理器"""

    def test_default_config(self, tmp_path: Path):
        cfg = Config(config_path=tmp_path / "config.toml")
        assert cfg.get("general.daily_count") == 50
        assert cfg.get("general.default_band") == 7

    def test_get_nonexistent_key(self, tmp_path: Path):
        cfg = Config(config_path=tmp_path / "config.toml")
        assert cfg.get("nonexistent") is None
        assert cfg.get("nonexistent", "default") == "default"

    def test_get_nested_nonexistent(self, tmp_path: Path):
        cfg = Config(config_path=tmp_path / "config.toml")
        assert cfg.get("general.nonexistent") is None
        assert cfg.get("a.b.c") is None

    def test_set_and_get(self, tmp_path: Path):
        cfg = Config(config_path=tmp_path / "config.toml")
        cfg.set("general.daily_count", 100)
        assert cfg.get("general.daily_count") == 100

    def test_set_new_section(self, tmp_path: Path):
        cfg = Config(config_path=tmp_path / "config.toml")
        cfg.set("new_section.key", "value")
        assert cfg.get("new_section.key") == "value"

    def test_save_and_reload(self, tmp_path: Path):
        config_path = tmp_path / "config.toml"
        cfg1 = Config(config_path=config_path)
        cfg1.set("general.daily_count", 100)
        cfg1.save()

        cfg2 = Config(config_path=config_path)
        assert cfg2.get("general.daily_count") == 100

    def test_ensure_app_dir(self, tmp_path: Path):
        config_path = tmp_path / "subdir" / "config.toml"
        cfg = Config(config_path=config_path)
        app_dir = cfg.ensure_app_dir()
        assert app_dir.exists()
        assert app_dir == config_path.parent

    def test_get_deep_nesting_with_non_dict(self, tmp_path: Path):
        cfg = Config(config_path=tmp_path / "config.toml")
        cfg.set("general.daily_count", 50)
        # Try to get a nested key from an int value
        assert cfg.get("general.daily_count.something") is None
