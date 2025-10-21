"""Configuration loading and validation for AIOrg."""

import logging
import sys
from pathlib import Path
from typing import Any

# Handle tomli vs tomllib for different Python versions
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        raise ImportError(
            "tomli is required for Python < 3.11. Install it with: pip install tomli"
        )

logger = logging.getLogger(__name__)


def get_default_config() -> dict[str, Any]:
    """
    Return default configuration values.

    Returns:
        dict: Default configuration
    """
    return {
        "settings": {
            "theme": "system",
            "log_level": "INFO",
            "database_path": "~/.aiorg/aiorg.db",
            "window_width": 1400,
            "window_height": 800,
            "split_ratio": 0.5,
        },
        "ai_models": [],
    }


def validate_config(config: dict[str, Any]) -> list[str]:
    """
    Validate configuration structure and values.

    Args:
        config: Configuration dictionary to validate

    Returns:
        list[str]: List of validation errors (empty if valid)
    """
    errors = []

    # Validate settings section exists
    if "settings" not in config:
        errors.append("Missing 'settings' section in configuration")
        return errors  # Cannot continue validation without settings

    settings = config["settings"]

    # Validate theme
    if "theme" in settings:
        valid_themes = ["dark", "light", "system"]
        if settings["theme"] not in valid_themes:
            errors.append(
                f"Invalid theme '{settings['theme']}'. Must be one of: {', '.join(valid_themes)}"
            )

    # Validate log_level
    if "log_level" in settings:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if settings["log_level"] not in valid_levels:
            errors.append(
                f"Invalid log_level '{settings['log_level']}'. Must be one of: {', '.join(valid_levels)}"
            )

    # Validate window dimensions
    if "window_width" in settings:
        if not isinstance(settings["window_width"], int) or settings["window_width"] <= 0:
            errors.append("window_width must be a positive integer")

    if "window_height" in settings:
        if not isinstance(settings["window_height"], int) or settings["window_height"] <= 0:
            errors.append("window_height must be a positive integer")

    # Validate split_ratio
    if "split_ratio" in settings:
        if not isinstance(settings["split_ratio"], (int, float)):
            errors.append("split_ratio must be a number")
        elif not (0.0 <= settings["split_ratio"] <= 1.0):
            errors.append("split_ratio must be between 0.0 and 1.0")

    # Validate ai_models
    if "ai_models" in config:
        if not isinstance(config["ai_models"], list):
            errors.append("ai_models must be a list")
        else:
            for i, model in enumerate(config["ai_models"]):
                # Check required fields
                if "name" not in model:
                    errors.append(f"AI model at index {i} is missing 'name' field")
                if "type" not in model:
                    errors.append(f"AI model at index {i} is missing 'type' field")
                elif model["type"] not in ["commercial", "local"]:
                    errors.append(
                        f"AI model '{model.get('name', f'at index {i}')}' has invalid type '{model['type']}'. "
                        "Must be 'commercial' or 'local'"
                    )
                if "url" not in model:
                    errors.append(f"AI model at index {i} is missing 'url' field")

                # Check local model specific requirements
                if model.get("type") == "local" and "model" not in model:
                    errors.append(
                        f"Local AI model '{model.get('name', f'at index {i}')}' is missing 'model' field"
                    )

    return errors


def load_config(config_path: str = "config.toml") -> dict[str, Any]:
    """
    Load and parse TOML configuration file.

    Args:
        config_path: Path to TOML configuration file

    Returns:
        dict: Parsed configuration with defaults applied

    Raises:
        FileNotFoundError: If config file doesn't exist
        tomli.TOMLDecodeError: If config file is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load TOML file
    with open(config_file, "rb") as f:
        config = tomllib.load(f)

    logger.info(f"Loaded configuration from {config_path}")

    # Get defaults
    defaults = get_default_config()

    # Apply defaults for missing settings
    if "settings" not in config:
        config["settings"] = {}

    for key, value in defaults["settings"].items():
        if key not in config["settings"]:
            config["settings"][key] = value
            logger.debug(f"Applied default value for settings.{key}: {value}")

    # Apply default for ai_models
    if "ai_models" not in config:
        config["ai_models"] = defaults["ai_models"]
        logger.warning("No AI models defined in configuration")

    # Validate configuration
    validation_errors = validate_config(config)
    if validation_errors:
        for error in validation_errors:
            logger.error(f"Configuration validation error: {error}")
        raise ValueError(f"Configuration validation failed: {'; '.join(validation_errors)}")

    # Expand paths (e.g., ~ to home directory)
    if "database_path" in config["settings"]:
        db_path = config["settings"]["database_path"]
        expanded_path = Path(db_path).expanduser()
        config["settings"]["database_path"] = str(expanded_path)
        logger.debug(f"Expanded database_path from {db_path} to {expanded_path}")

    logger.info(f"Configuration loaded successfully with {len(config.get('ai_models', []))} AI models")

    return config
