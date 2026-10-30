"""Backward-compatible entry point for build_dataset_manifests.py."""
from build_dataset_manifests import main

if __name__ == "__main__":
    import sys
    main(*sys.argv[1:])
