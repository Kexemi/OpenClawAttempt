#!/usr/bin/env python3
"""
Warmup and startup: verify setup, then launch the preview server.
Run this before generating content. Double-click start.bat (Windows) or run:
    python scripts/startup.py

Optionally pass --generate to run a batch generation first.
"""
import subprocess
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    print("=" * 50)
    print("Nostalgia pipeline – warmup & startup")
    print("=" * 50)

    # 1. Verify setup
    print("\n[1/3] Verifying setup...")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "verify_setup.py")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr or result.stdout)
        print("\nFix the errors above, then run startup again.")
        sys.exit(1)
    print("  Setup OK.")

    # 2. Optional: generate batch
    if "--generate" in sys.argv:
        print("\n[2/3] Generating batch...")
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_batch.py")],
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            print("  Generation had errors (check output above).")
            sys.exit(1)
        print("  Batch complete.")
    else:
        print("\n[2/3] Skipping generation (use --generate to run generate_batch).")

    # 3. Start preview server
    print("\n[3/3] Starting preview server...")
    print("  Open http://localhost:8080 in your browser")
    print("  Press Ctrl+C to stop")
    print("-" * 50)

    # Open browser after a short delay (Flask will be ready)
    import threading
    import time

    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8080")

    threading.Thread(target=open_browser, daemon=True).start()

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "preview" / "app.py")],
        cwd=PROJECT_ROOT,
    )


if __name__ == "__main__":
    main()
