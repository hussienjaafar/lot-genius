#!/usr/bin/env python3
"""
Demo bundle generator for Lot Genius.
Creates a self-contained demo zip with sample data and getting started guide.
"""

import os
import zipfile
from pathlib import Path
import sys

def create_demo_zip():
    """Create lotgenius_demo.zip with demo files and documentation."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Define source paths
    demo_dir = repo_root / "examples" / "demo"
    getting_started = repo_root / "docs" / "GETTING_STARTED.md"

    # Define output path
    demo_zip_path = repo_root / "lotgenius_demo.zip"

    # Check that all required files exist
    required_files = [
        demo_dir / "demo_manifest.csv",
        demo_dir / "demo_opt.json",
        demo_dir / "demo_readme.txt",
        getting_started
    ]

    missing_files = [f for f in required_files if not f.exists()]
    if missing_files:
        print(f"Error: Missing required files: {missing_files}", file=sys.stderr)
        return False

    print(f"Creating demo bundle: {demo_zip_path}")

    # Create the zip file
    try:
        with zipfile.ZipFile(demo_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add demo files (preserve demo/ directory structure)
            for file_path in demo_dir.iterdir():
                if file_path.is_file():
                    archive_path = f"demo/{file_path.name}"
                    zf.write(file_path, archive_path)
                    print(f"  Added: {archive_path}")

            # Add getting started guide at root level
            zf.write(getting_started, "GETTING_STARTED.md")
            print(f"  Added: GETTING_STARTED.md")

        # Verify the zip file was created successfully
        if demo_zip_path.exists():
            size_mb = demo_zip_path.stat().st_size / (1024 * 1024)
            print(f"Success: Created {demo_zip_path} ({size_mb:.2f} MB)")

            # List contents for verification
            print("\nBundle contents:")
            with zipfile.ZipFile(demo_zip_path, 'r') as zf:
                for info in zf.infolist():
                    size_kb = info.file_size / 1024
                    print(f"  {info.filename} ({size_kb:.1f} KB)")

            return True
        else:
            print("Error: Failed to create demo zip file", file=sys.stderr)
            return False

    except Exception as e:
        print(f"Error creating demo zip: {e}", file=sys.stderr)
        return False

def main():
    """Main entry point."""
    success = create_demo_zip()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
