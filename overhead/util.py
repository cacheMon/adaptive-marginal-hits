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

def read_configs():
    """Read configuration from configs.json file."""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, "configs.json")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return config
    except (FileNotFoundError, IOError) as e:
        raise RuntimeError(f"Could not read configs.json ({e}). Please ensure {config_file} exists and is readable.")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in configs.json ({e}). Please check the file format.")

# Read configuration values
username = get_username()
configs = read_configs()
CACHEBENCH_BINARY_PATH = configs['cachelib_path']
MOCK_TIMER_PATH = f"/users/{username}/libmock_time.so"

def read_overhead_configs():
    """Read configuration from configs.json file in the overhead directory."""
    try:
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, "configs.json")
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return config
    except (FileNotFoundError, IOError) as e:
        raise RuntimeError(f"Could not read configs.json ({e}). Please ensure {config_file} exists and is readable.")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON in configs.json ({e}). Please check the file format.")


def dict_hash(d):
    # Serialize with sorted keys and no whitespace for consistency
    json_str = json.dumps(d, sort_keys=True, separators=(',', ':'))
    return hashlib.md5(json_str.encode('utf-8')).hexdigest()

def run_cachebench(top_dir, repeat=3):
    config_file = os.path.join(top_dir, "config.json")
    meta_file = os.path.join(top_dir, "meta.json")
    rc_file = os.path.join(top_dir, "rc.txt")

    with open(meta_file, 'r') as f:
        meta_content = json.load(f)
    with open(config_file, 'r') as f:
        config_content = json.load(f)

    cachelib_path = CACHEBENCH_BINARY_PATH

    for i in range(repeat):
        output_file = os.path.join(top_dir, f"result_{i}.json")
        log_file = os.path.join(top_dir, f"log_{i}.txt")
        tx_file = os.path.join(top_dir, f"tx_{i}")

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

        with open(log_file, 'w') as out:
            result = subprocess.run(" ".join(command), shell=True, stdout=out, stderr=subprocess.STDOUT)
        # allow failures (lama compatible)
        # if result.returncode != 0:
        #     with open(rc_file, 'w') as rc_out:
        #         rc_out.write(str(result.returncode) + "\n")
        #     return result.returncode

    # If all runs succeed, write last return code (should be 0)
    with open(rc_file, 'w') as rc_out:
        rc_out.write(str(result.returncode) + "\n")
    return result.returncode
