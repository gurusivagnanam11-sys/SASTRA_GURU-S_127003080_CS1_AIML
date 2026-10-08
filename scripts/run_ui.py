"""Launcher script for AUTOSAR HLD Streamlit UI.

Usage:
    python scripts/run_ui.py [--port 8501]
"""

import argparse
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(
        description="Run AUTOSAR HLD Streamlit Pilot UI"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run Streamlit on",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host interface to bind",
    )
    args = parser.parse_args()

    app_path = PROJECT_ROOT / "app" / "streamlit_app.py"

    if not app_path.exists():
        print(
            f"Error: UI script not found at {app_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        f"--server.port={args.port}",
        f"--server.address={args.host}",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]

    print(
        f"Starting AUTOSAR HLD Assistant UI at "
        f"http://localhost:{args.port}..."
    )

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nUI stopped by user.")


if __name__ == "__main__":
    main()