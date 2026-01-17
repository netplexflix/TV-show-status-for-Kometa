"""Configuration loading and management for TSSK"""

import os
import sys
import yaml

from .constants import IS_DOCKER, GREEN, ORANGE, RED, RESET


def get_output_directory():
    """
    Determine the output directory for YAML files.
    Priority order:
    1. TSSK_OUTPUT_DIR environment variable (set by entrypoint)
    2. /config/kometa/tssk if /config/kometa exists and is writable (backwards compatible)
    3. /app/kometa (new default for unRAID and other platforms)
    4. kometa/ (non-Docker local usage)
    """
    if not IS_DOCKER:
        return "kometa/"
    
    # Check for environment variable first (set by entrypoint script)
    env_output_dir = os.getenv("TSSK_OUTPUT_DIR")
    if env_output_dir:
        return env_output_dir.rstrip('/') + '/'
    
    # Check /config/kometa first (backwards compatible with existing docker-compose setups)
    config_kometa = "/config/kometa"
    if os.path.isdir(config_kometa):
        try:
            # Test if writable
            test_file = os.path.join(config_kometa, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            # Use the tssk subfolder for backwards compatibility
            return config_kometa + "/tssk/"
        except (IOError, OSError):
            pass
    
    # Fall back to /app/kometa (works with unRAID template mapping to /app/kometa)
    return "/app/kometa/"


def ensure_output_directory():
    """Ensure the output directory exists and is writable"""
    output_dir = get_output_directory()
    try:
        os.makedirs(output_dir, exist_ok=True)
        # Test write permissions
        test_file = os.path.join(output_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return output_dir
    except Exception as e:
        print(f"{RED}Error: Cannot write to output directory {output_dir}: {str(e)}{RESET}")
        print(f"{RED}Please ensure the directory exists and has proper permissions.{RESET}")
        sys.exit(1)


def load_config(file_path='config/config.yml'):
    """Load the main configuration file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Config file '{file_path}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML config file: {e}")
        sys.exit(1)


def load_localization(file_path='config/localization.yml'):
    """Load localization settings with English defaults"""
    # English defaults
    default_localization = {
        'simplify_next_week': {
            'use_abbreviated': False,
            'today': 'today',
            'tomorrow': 'tomorrow'
        },
        'months_full': {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        },
        'months_abbr': {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
            5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
            9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        },
        'weekdays_full': {
            0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
            4: 'Friday', 5: 'Saturday', 6: 'Sunday'
        },
        'weekdays_abbr': {
            0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu',
            4: 'Fri', 5: 'Sat', 6: 'Sun'
        }
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            user_localization = yaml.safe_load(file)
            
            if user_localization:
                # Merge user localization with defaults
                # Deep merge for nested dictionaries
                for key in default_localization:
                    if key in user_localization:
                        if isinstance(default_localization[key], dict):
                            default_localization[key].update(user_localization[key])
                        else:
                            default_localization[key] = user_localization[key]
    except FileNotFoundError:
        # Silently use defaults if file doesn't exist
        pass
    except yaml.YAMLError as e:
        print(f"{ORANGE}Warning: Error parsing localization file, using English defaults: {e}{RESET}")
    except Exception as e:
        print(f"{ORANGE}Warning: Could not load localization file, using English defaults: {e}{RESET}")
    
    return default_localization


def get_config_section(config, primary_key, fallback_keys=None):
    """Get a configuration section with fallback support"""
    if fallback_keys is None:
        fallback_keys = []
    
    if primary_key in config:
        return config[primary_key]
    
    for key in fallback_keys:
        if key in config:
            return config[key]
    
    return {}