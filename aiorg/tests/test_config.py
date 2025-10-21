"""Unit tests for configuration loading and validation.

Tests the config module for TOML parsing, validation, and defaults.
"""

import pytest
import tempfile
from pathlib import Path
from ai_viewer.config import load_config, get_default_config, validate_config


class TestGetDefaultConfig:
    """Test suite for get_default_config function."""

    def test_returns_dict(self):
        """Test that get_default_config returns a dictionary."""
        config = get_default_config()
        assert isinstance(config, dict)

    def test_has_settings_section(self):
        """Test that default config has settings section."""
        config = get_default_config()
        assert "settings" in config
        assert isinstance(config["settings"], dict)

    def test_has_ai_models_section(self):
        """Test that default config has ai_models section."""
        config = get_default_config()
        assert "ai_models" in config
        assert isinstance(config["ai_models"], list)

    def test_default_settings_values(self):
        """Test default settings values."""
        config = get_default_config()
        settings = config["settings"]

        assert settings["theme"] == "system"
        assert settings["log_level"] == "INFO"
        assert settings["database_path"] == "~/.aiorg/aiorg.db"
        assert settings["window_width"] == 1400
        assert settings["window_height"] == 800
        assert settings["split_ratio"] == 0.5

    def test_default_ai_models_empty(self):
        """Test that default ai_models is empty list."""
        config = get_default_config()
        assert config["ai_models"] == []


class TestValidateConfig:
    """Test suite for validate_config function."""

    def test_valid_config_no_errors(self):
        """Test that valid config returns no errors."""
        config = {
            "settings": {
                "theme": "dark",
                "log_level": "DEBUG",
                "database_path": "~/.aiorg/aiorg.db",
                "window_width": 1200,
                "window_height": 800,
                "split_ratio": 0.6,
            },
            "ai_models": [
                {"name": "Claude", "type": "commercial", "url": "https://claude.ai"},
                {"name": "Llama", "type": "local", "url": "http://localhost:11434", "model": "llama2"}
            ]
        }

        errors = validate_config(config)
        assert errors == []

    def test_missing_settings_section(self):
        """Test validation error for missing settings section."""
        config = {"ai_models": []}
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("settings" in error.lower() for error in errors)

    def test_invalid_theme(self):
        """Test validation error for invalid theme."""
        config = {
            "settings": {"theme": "invalid_theme"},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("theme" in error.lower() for error in errors)

    def test_valid_themes(self):
        """Test that valid themes pass validation."""
        for theme in ["dark", "light", "system"]:
            config = {
                "settings": {"theme": theme},
                "ai_models": []
            }
            errors = validate_config(config)
            assert not any("theme" in error.lower() for error in errors)

    def test_invalid_log_level(self):
        """Test validation error for invalid log level."""
        config = {
            "settings": {"log_level": "INVALID"},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("log_level" in error.lower() for error in errors)

    def test_valid_log_levels(self):
        """Test that valid log levels pass validation."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            config = {
                "settings": {"log_level": level},
                "ai_models": []
            }
            errors = validate_config(config)
            assert not any("log_level" in error.lower() for error in errors)

    def test_invalid_window_width_negative(self):
        """Test validation error for negative window width."""
        config = {
            "settings": {"window_width": -100},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("window_width" in error.lower() for error in errors)

    def test_invalid_window_width_zero(self):
        """Test validation error for zero window width."""
        config = {
            "settings": {"window_width": 0},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("window_width" in error.lower() for error in errors)

    def test_invalid_window_height(self):
        """Test validation error for invalid window height."""
        config = {
            "settings": {"window_height": -50},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("window_height" in error.lower() for error in errors)

    def test_invalid_split_ratio_too_low(self):
        """Test validation error for split_ratio < 0."""
        config = {
            "settings": {"split_ratio": -0.1},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("split_ratio" in error.lower() for error in errors)

    def test_invalid_split_ratio_too_high(self):
        """Test validation error for split_ratio > 1."""
        config = {
            "settings": {"split_ratio": 1.5},
            "ai_models": []
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("split_ratio" in error.lower() for error in errors)

    def test_valid_split_ratio_boundary_values(self):
        """Test that boundary values for split_ratio are valid."""
        for ratio in [0.0, 0.5, 1.0]:
            config = {
                "settings": {"split_ratio": ratio},
                "ai_models": []
            }
            errors = validate_config(config)
            assert not any("split_ratio" in error.lower() for error in errors)

    def test_ai_models_not_a_list(self):
        """Test validation error when ai_models is not a list."""
        config = {
            "settings": {},
            "ai_models": "not a list"
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("ai_models" in error.lower() and "list" in error.lower() for error in errors)

    def test_ai_model_missing_name(self):
        """Test validation error for model missing name."""
        config = {
            "settings": {},
            "ai_models": [
                {"type": "commercial", "url": "https://example.com"}
            ]
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("name" in error.lower() for error in errors)

    def test_ai_model_missing_type(self):
        """Test validation error for model missing type."""
        config = {
            "settings": {},
            "ai_models": [
                {"name": "Test", "url": "https://example.com"}
            ]
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("type" in error.lower() for error in errors)

    def test_ai_model_missing_url(self):
        """Test validation error for model missing url."""
        config = {
            "settings": {},
            "ai_models": [
                {"name": "Test", "type": "commercial"}
            ]
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("url" in error.lower() for error in errors)

    def test_ai_model_invalid_type(self):
        """Test validation error for invalid model type."""
        config = {
            "settings": {},
            "ai_models": [
                {"name": "Test", "type": "invalid", "url": "https://example.com"}
            ]
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("type" in error.lower() and "invalid" in error.lower() for error in errors)

    def test_local_model_missing_model_field(self):
        """Test validation error for local model missing 'model' field."""
        config = {
            "settings": {},
            "ai_models": [
                {"name": "Llama", "type": "local", "url": "http://localhost:11434"}
            ]
        }
        errors = validate_config(config)

        assert len(errors) > 0
        assert any("model" in error.lower() for error in errors)

    def test_commercial_model_valid_without_model_field(self):
        """Test that commercial model doesn't need 'model' field."""
        config = {
            "settings": {},
            "ai_models": [
                {"name": "Claude", "type": "commercial", "url": "https://claude.ai"}
            ]
        }
        errors = validate_config(config)

        # Should not have error about missing 'model' field
        assert not any("model" in error.lower() for error in errors)


class TestLoadConfig:
    """Test suite for load_config function."""

    def test_load_valid_config_file(self):
        """Test loading a valid TOML config file."""
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "dark"
log_level = "DEBUG"
database_path = "~/.aiorg/test.db"
window_width = 1200
window_height = 600
split_ratio = 0.7

[[ai_models]]
name = "Claude"
type = "commercial"
url = "https://claude.ai/chat"

[[ai_models]]
name = "Llama"
type = "local"
url = "http://localhost:11434"
model = "llama2"
""")
            temp_path = f.name

        try:
            config = load_config(temp_path)

            # Verify settings loaded correctly
            assert config["settings"]["theme"] == "dark"
            assert config["settings"]["log_level"] == "DEBUG"
            assert config["settings"]["window_width"] == 1200
            assert config["settings"]["window_height"] == 600
            assert config["settings"]["split_ratio"] == 0.7

            # Verify database path was expanded
            assert "~" not in config["settings"]["database_path"]

            # Verify models loaded correctly
            assert len(config["ai_models"]) == 2
            assert config["ai_models"][0]["name"] == "Claude"
            assert config["ai_models"][1]["name"] == "Llama"

        finally:
            Path(temp_path).unlink()

    def test_load_nonexistent_file(self):
        """Test loading non-existent config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.toml")

    def test_load_invalid_toml_syntax(self):
        """Test loading file with invalid TOML syntax raises error."""
        # Create temporary file with invalid TOML
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("invalid toml [[[[ syntax")
            temp_path = f.name

        try:
            with pytest.raises(Exception):  # tomllib.TOMLDecodeError
                load_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_with_validation_errors(self):
        """Test loading config with validation errors raises ValueError."""
        # Create temporary config file with invalid values
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "invalid_theme"
window_width = -100
""")
            temp_path = f.name

        try:
            with pytest.raises(ValueError) as exc_info:
                load_config(temp_path)

            # Verify error message contains validation issues
            assert "validation" in str(exc_info.value).lower()

        finally:
            Path(temp_path).unlink()

    def test_load_config_applies_defaults(self):
        """Test that missing settings get default values."""
        # Create minimal config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "dark"

[[ai_models]]
name = "Test"
type = "commercial"
url = "https://test.com"
""")
            temp_path = f.name

        try:
            config = load_config(temp_path)

            # Verify defaults were applied
            assert config["settings"]["log_level"] == "INFO"  # default
            assert config["settings"]["window_width"] == 1400  # default
            assert config["settings"]["window_height"] == 800  # default
            assert config["settings"]["split_ratio"] == 0.5  # default

        finally:
            Path(temp_path).unlink()

    def test_load_config_empty_models(self):
        """Test loading config with no AI models."""
        # Create config with no models
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "dark"
""")
            temp_path = f.name

        try:
            config = load_config(temp_path)

            # Verify ai_models is empty list
            assert config["ai_models"] == []

        finally:
            Path(temp_path).unlink()

    def test_path_expansion(self):
        """Test that tilde in database_path is expanded."""
        # Create config with tilde in path
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
database_path = "~/test/aiorg.db"
""")
            temp_path = f.name

        try:
            config = load_config(temp_path)

            # Verify tilde was expanded
            db_path = config["settings"]["database_path"]
            assert "~" not in db_path
            assert str(Path.home()) in db_path

        finally:
            Path(temp_path).unlink()

    def test_multiple_models_same_type(self):
        """Test loading config with multiple models of same type."""
        # Create config with multiple local models
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("""
[settings]
theme = "dark"

[[ai_models]]
name = "Llama 2"
type = "local"
url = "http://localhost:11434"
model = "llama2"

[[ai_models]]
name = "Mistral"
type = "local"
url = "http://localhost:11434"
model = "mistral"
""")
            temp_path = f.name

        try:
            config = load_config(temp_path)

            # Verify both models loaded
            assert len(config["ai_models"]) == 2
            assert config["ai_models"][0]["model"] == "llama2"
            assert config["ai_models"][1]["model"] == "mistral"

        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
