## { SCRIPT

##
## === DEPENDENCIES
##

## stdlib
import subprocess
import sys
import time

from pathlib import Path


##
## === MAIN PROGRAM
##


def main() -> None:
    ## discover all validation test files
    vtests_root = Path(__file__).parent
    test_files = sorted(vtests_root.glob("test_*.py"))
    if not test_files:
        print("No validation test files found.", flush=True)
        sys.exit(0)
    ## run each file separately so we can report per-file timing
    ## (conftest.py is picked up automatically by pytest for each file)
    print(f"Running validation tests ({len(test_files)} files)...\n", flush=True)
    results: list[tuple[str, bool, float]] = []
    for test_file in test_files:
        label = test_file.name
        start_time = time.perf_counter()
        process = subprocess.run(
            args=[sys.executable, "-m", "pytest", str(test_file), "-v"],
            text=True,
        )
        elapsed_time = time.perf_counter() - start_time
        passed = process.returncode == 0
        results.append((label, passed, elapsed_time))
        status = "pass" if passed else "FAIL"
        print(f"  {label}: {status} ({elapsed_time:.2f}s)\n", flush=True)
    ## summary
    num_passed = sum(1 for _, passed, _ in results if passed)
    num_total = len(results)
    total_elapsed_time = sum(elapsed_time for _, _, elapsed_time in results)
    print(f"{num_passed}/{num_total} passed in {total_elapsed_time:.2f}s.", flush=True)
    if num_passed < num_total:
        sys.exit(1)


##
## === ENTRY POINT
##

if __name__ == "__main__":
    main()

## } SCRIPT
