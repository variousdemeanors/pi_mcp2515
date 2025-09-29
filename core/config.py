import json
import os

CONFIG_PATH = 'config.json'
PRECONFIG_PATH = 'config.preconfigured_mcp2515.json'


def _load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def load_config():
    """Load configuration.

    Behavior for this preconfigured branch:
    - If `config.json` exists and is valid, return it.
    - If missing, but `config.preconfigured_mcp2515.json` exists, load that
      and copy it to `config.json` so the runtime uses a concrete file.
    - Force `datalogging.display_units` to 'imperial' for consistency.
    """
    try:
        if os.path.exists(CONFIG_PATH):
            cfg = _load_json(CONFIG_PATH)
            # Ensure display units default
            cfg.setdefault('datalogging', {})
            cfg['datalogging'].setdefault('display_units', 'imperial')
            return cfg

        if os.path.exists(PRECONFIG_PATH):
            print(f"Configuration not found at {CONFIG_PATH}; using preconfigured profile {PRECONFIG_PATH}.")
            cfg = _load_json(PRECONFIG_PATH)
            cfg.setdefault('datalogging', {})
            cfg['datalogging']['display_units'] = 'imperial'
            # Persist the preconfigured config as config.json so other tools behave normally
            try:
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(cfg, f, indent=2)
                print(f"Wrote preconfigured config to {CONFIG_PATH}")
            except Exception as e:
                print(f"Warning: could not write {CONFIG_PATH}: {e}")
            return cfg

        print(f"ERROR: No configuration found ({CONFIG_PATH} nor {PRECONFIG_PATH}).")
        return None
    except json.JSONDecodeError:
        print(f"ERROR: Configuration file is not a valid JSON file.")
        return None


def save_config(config_data):
    """Saves the given configuration data to config.json."""
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        print(f"ERROR: Could not save configuration to {CONFIG_PATH}. Error: {e}")
        return False
