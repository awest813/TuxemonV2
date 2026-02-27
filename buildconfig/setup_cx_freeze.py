#!/usr/bin/python
"""
Responsible for building the Windows binary package of the
game with cx_Freeze and Python 3.10+

To build the package on Windows, run the following command on Windows:
    `python buildconfig/setup_cx_freeze.py build`

"win32" is just the name used by cx_freeze and doesn't mean it is a 32-bit app.

DO NOT RUN FROM A VENV.  YOU WILL BE MET WITH INSURMOUNTABLE SORROW.
"""

import logging
import os
import sys
from pathlib import Path

# Ensure imports work whether the script is run from the repo root or
# from inside buildconfig/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cx_Freeze import Executable, setup

from tuxemon.database.yaml_utils import load_yaml

logger = logging.getLogger(__name__)

# prevent SDL from opening a window
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "disk"


def load_config(config_file: str = "build_config.yaml"):
    config_path = Path(config_file)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent / config_path

    try:
        return load_yaml(config_path)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    config = load_config()

    build_exe_options = {
        "packages": config["packages"],
        "excludes": config["excludes"],
        "includes": config["includes"],
        "include_files": config["include_files"],
    }

    setup(
        name=config["name"],
        version=config["version"],
        options={"build_exe": build_exe_options},
        description=config["description"],
        executables=[
            Executable(
                config["executable"],
                base=config["base"],
                icon=config["icon"],
            )
        ],
    )
    logger.info("Build completed successfully.")
