# src/core/config.py
"""
Configuration Management for AI E2E Testing Agent
Handles loading, validation, and environment variable substitution
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class ConfigValidationResult:
    """Result of configuration validation"""
    valid: bool
    errors: list
    warnings: list

def load_config(config_path: str = "config/app_config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file with environment variable substitution
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary containing configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load environment variables from .env file if it exists
    env_file = config_file.parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        logger.info(f"Loaded environment variables from {env_file}")
    
    # Load YAML configuration
    try:
        with open(config_file, 'r') as f:
            config_content = f.read()
        
        # Substitute environment variables
        config_content = substitute_env_variables(config_content)
        
        # Parse YAML
        config = yaml.safe_load(config_content)
        
        logger.info(f"Configuration loaded from {config_path}")
        
        # Validate configuration
        validation_result = validate_config(config)
        
        if not validation_result.valid:
            error_msg = f"Configuration validation failed: {', '.join(validation_result.errors)}"
            raise ValueError(error_msg)
        
        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.warning(f"Configuration warning: {warning}")
        
        return config
        
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML configuration: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")

def substitute_env_variables(content: str) -> str:
    """
    Substitute environment variables in configuration content
    Supports ${VAR_NAME} and ${VAR_NAME:default_value} syntax
    """
    
    import re
    
    def replace_var(match):
        var_expr = match.group(1)
        
        if ':' in var_expr:
            # Variable with default value
            var_name, default_value = var_expr.split(':', 1)
            return os.getenv(var_name.strip(), default_value.strip())
        else:
            # Variable without default
            var_name = var_expr.strip()
            value = os.getenv(var_name)
            if value is None:
                raise ValueError(f"Environment variable '{var_name}' is required but not set")
            return value
    
    # Pattern to match ${VAR_NAME} or ${VAR_NAME:default}
    pattern = r'\$\{([^}]+)\}'
    
    try:
        return re.sub(pattern, replace_var, content)
    except Exception as e:
        raise ValueError(f"Environment variable substitution failed: {e}")

def validate_config(config: Dict[str, Any]) -> ConfigValidationResult:
    """
    Validate configuration structure and required fields
    
    Args:
        config: Configuration dictionary
        
    Returns:
        ConfigValidationResult with validation status
    """
    
    errors = []
    warnings = []
    
    # Check required top-level sections
    required_sections = ['azure_openai', 'browser_config', 'agents']
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")
    
    # Validate Azure OpenAI configuration
    if 'azure_openai' in config:
        azure_config = config['azure_openai']
        
        required_azure_fields = ['endpoint', 'api_key', 'deployment_name', 'api_version']
        for field in required_azure_fields:
            if field not in azure_config or not azure_config[field]:
                errors.append(f"Missing or empty Azure OpenAI field: {field}")
        
        # Validate endpoint format
        if 'endpoint' in azure_config:
            endpoint = azure_config['endpoint']
            if not endpoint.startswith('https://') or not endpoint.endswith('.openai.azure.com/'):
                warnings.append("Azure OpenAI endpoint format may be incorrect")
        
        # Validate deployment name
        if 'deployment_name' in azure_config:
            deployment = azure_config['deployment_name']
            if not deployment or deployment == "your-deployment-name":
                errors.append("Azure OpenAI deployment_name must be configured")
    
    # Validate browser configuration
    if 'browser_config' in config:
        browser_config = config['browser_config']
        
        valid_browser_types = ['chromium', 'firefox', 'webkit']
        if 'type' in browser_config:
            if browser_config['type'] not in valid_browser_types:
                errors.append(f"Invalid browser type. Must be one of: {valid_browser_types}")
    
    # Validate agents configuration
    if 'agents' in config:
        agents_config = config['agents']
        
        expected_agents = ['nl_processor', 'test_strategy', 'test_generation']
        for agent in expected_agents:
            if agent not in agents_config:
                warnings.append(f"Missing agent configuration: {agent}")
            else:
                agent_config = agents_config[agent]
    
    
    return ConfigValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def setup_logging(level: str = "INFO", output_dir: str = "./logs"):
    """
    Setup logging configuration
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        output_dir: Directory for log files
    """
    
    # Create logs directory
    log_dir = Path(output_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    
    # Setup file handler
    log_file = log_dir / "ai_e2e_agent.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Always log everything to file
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logger.info(f"Logging configured - Level: {level}, Output: {log_file}")

def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration structure
    Useful for initialization and testing
    """
    
    return {
        "azure_openai": {
            "endpoint": "${AZURE_OPENAI_ENDPOINT}",
            "api_key": "${AZURE_OPENAI_API_KEY}",
            "deployment_name": "gpt-4.1",
            "api_version": "2024-10-21"
        },
        "application": {
            "name": "Legacy Java Application",
            "type": "legacy_java",
            "default_timeout": 30000,
            "slow_mo": 1000
        },
        "browser_config": {
            "type": "chromium",
            "headless": True,
            "viewport": {
                "width": 1920,
                "height": 1080
            },
            "context_options": {
                "ignore_https_errors": True,
                "accept_downloads": False
            },
            "launch_options": {
                "slow_mo": 1000,
                "args": [
                    "--disable-web-security",
                    "--ignore-certificate-errors",
                    "--allow-running-insecure-content"
                ]
            }
        },
        "storage": {
            "base_path": "./test_data",
            "results_retention_days": 30,
            "enable_compression": False
        },
        "agents": {
            "nl_processor": {
                "temperature": 0.1
            },
            "test_strategy": {
                "temperature": 0.1
            },
            "test_generation": {
                "temperature": 0.1
            },
            "element_detection": {
                "temperature": 0.2
            },
            "self_healing": {
                "temperature": 0.2
            }
        },
        "reporting": {
            "enable_console": True,
            "enable_html": True,
            "enable_screenshots": True,
            "screenshot_on_failure": True,
            "detailed_logging": True
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "file_output": "./logs/ai_e2e_agent.log"
        }
    }

def save_config(config: Dict[str, Any], output_path: str):
    """
    Save configuration to YAML file
    
    Args:
        config: Configuration dictionary
        output_path: Path to save configuration
    """
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)
    
    logger.info(f"Configuration saved to {output_path}")

def create_env_template(output_path: str = "config/.env.template"):
    """
    Create environment variables template file
    
    Args:
        output_path: Path to save template
    """
    
    template_content = """# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here

# Optional: Application-specific settings
TARGET_APPLICATION_URL=https://your-application.com
TEST_USERNAME=admin
TEST_PASSWORD=your-password

# Optional: Development settings
DEBUG=false
LOG_LEVEL=INFO
"""
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write(template_content)
    
    logger.info(f"Environment template created at {output_path}")

# Testing and validation functions
def test_config_loading():
    """Test configuration loading with various scenarios"""
    
    print("Testing configuration management...")
    
    # Test 1: Default configuration
    default_config = get_default_config()
    validation_result = validate_config(default_config)
    
    print(f"Default config validation: {'✅' if validation_result.valid else '❌'}")
    if validation_result.errors:
        print(f"  Errors: {validation_result.errors}")
    if validation_result.warnings:
        print(f"  Warnings: {validation_result.warnings}")
    
    # Test 2: Environment variable substitution
    test_content = """
    azure_openai:
      endpoint: ${AZURE_OPENAI_ENDPOINT:https://default.openai.azure.com/}
      api_key: ${AZURE_OPENAI_API_KEY}
    """
    
    try:
        # Set test environment variable
        os.environ['AZURE_OPENAI_API_KEY'] = 'test-key'
        
        substituted = substitute_env_variables(test_content)
        print("✅ Environment variable substitution working")
        
        # Clean up
        del os.environ['AZURE_OPENAI_API_KEY']
        
    except Exception as e:
        print(f"❌ Environment variable substitution failed: {e}")
    
    print("Configuration management tests completed!")

if __name__ == "__main__":
    # Run tests
    test_config_loading()
    
    # Create example files
    try:
        # Save default configuration
        default_config = get_default_config()
        save_config(default_config, "example_config.yaml")
        print("✅ Example configuration saved to example_config.yaml")
        
        # Create environment template
        create_env_template("example.env")
        print("✅ Environment template saved to example.env")
        
    except Exception as e:
        print(f"❌ Error creating example files: {e}")