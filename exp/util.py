import json
import hashlib
import os
import json
import re
import subprocess
from const import *


def get_username():
    """Read username from the configuration file."""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to find the hosts directory
        username_file = os.path.join(script_dir, "..", "hosts", "username.txt")
        
        with open(username_file, 'r') as f:
            username = f.read().strip()
        return username
    except (FileNotFoundError, IOError) as e:
        # Throw error instead of using fallback
        raise RuntimeError(f"Could not read username from config file ({e}). Please ensure {username_file} exists and is readable.")


def get_config_paths():
    """Read configuration paths from configs.json file."""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # configs.json is in the same directory as this script
        config_file = os.path.join(script_dir, "configs.json")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check that required fields exist
        if 'wget_trace_path' not in config:
            raise ValueError(f"Missing required field 'wget_trace_path' in {config_file}")
        if 'local_trace_file_dir' not in config:
            raise ValueError(f"Missing required field 'local_trace_file_dir' in {config_file}")
        
        return {
            'WGET_PATH': config['wget_trace_path'],
            'TRACE_FILE_PATH': config['local_trace_file_dir']
        }
    except (FileNotFoundError, IOError) as e:
        # Throw error instead of using fallback
        raise RuntimeError(f"Could not read config paths from configs.json ({e}). Please ensure {config_file} exists and is readable.")
    except json.JSONDecodeError as e:
        # Throw error for invalid JSON
        raise RuntimeError(f"Invalid JSON in configs.json ({e}). Please check the file format.")


def get_dynamic_paths():
    """Generate paths dynamically based on the configured username."""
    username = get_username()
    
    paths = {
        'CACHEBENCH_BINARY_PATH': f"/users/{username}/cachelib_v1/opt/cachelib/bin/cachebench",
        'CACHEBENCH_BINARY_PATH2': f"/users/{username}/cachelib_v2/opt/cachelib/bin/cachebench",
        'MOCK_TIMER_PATH': f"/users/{username}/libmock_time.so"
    }
    
    return paths


# Get dynamic paths
_dynamic_paths = get_dynamic_paths()
CACHEBENCH_BINARY_PATH = _dynamic_paths['CACHEBENCH_BINARY_PATH']
CACHEBENCH_BINARY_PATH2 = _dynamic_paths['CACHEBENCH_BINARY_PATH2']
MOCK_TIMER_PATH = _dynamic_paths['MOCK_TIMER_PATH']

# Get config paths
_config_paths = get_config_paths()
WGET_PATH = _config_paths['WGET_PATH']
TRACE_FILE_PATH = _config_paths['TRACE_FILE_PATH']


def dict_hash(d):
    # Serialize with sorted keys and no whitespace for consistency
    json_str = json.dumps(d, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()

def run_cachebench(top_dir, repeat=1):
    config_file = os.path.join(top_dir, "config.json")
    meta_file = os.path.join(top_dir, "meta.json")
    output_file = os.path.join(top_dir, "result.json")
    log_file = os.path.join(top_dir, "log.txt")
    tx_file = os.path.join(top_dir, "tx")
    
    with open(meta_file, 'r') as f:
        meta_content = json.load(f)
    with open(config_file, 'r') as f:
        config_content = json.load(f)
    
    cachelib_path = CACHEBENCH_BINARY_PATH2 if int(meta_content["slab_size"]) == 1 else CACHEBENCH_BINARY_PATH

    if config_content["test_config"]["useTraceTimer"]:
        command = [
            f'LD_PRELOAD="{MOCK_TIMER_PATH}"',
            f'MOCK_TIMER_LIB_PATH="{MOCK_TIMER_PATH}"',
            cachelib_path,
            "--json_test_config", config_file,
            "--dump_result_json_file", output_file,
            "--dump_tx_file", tx_file,
            "--disable_progress_tracker=true"
        ]
    else:
        command = [
            cachelib_path,
            "--json_test_config", config_file,
            "--dump_result_json_file", output_file,
            "--dump_tx_file", tx_file,
            "--disable_progress_tracker=true"
        ]

    rc_file = os.path.join(top_dir, "rc.txt")
    for i in range(repeat):
        with open(log_file, 'w') as out:
            result = subprocess.run(" ".join(command), shell=True, stdout=out, stderr=subprocess.STDOUT)
        if result.returncode != 0:
            with open(rc_file, 'w') as rc_out:
                rc_out.write(str(result.returncode) + "\n")
            return result.returncode
    # If all runs succeed, write last return code (should be 0)
    with open(rc_file, 'w') as rc_out:
        rc_out.write(str(result.returncode) + "\n")
    return result.returncode