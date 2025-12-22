import subprocess
from pathlib import Path
from core.paths import STACKS_DIR

def run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True)

def main():
    stack = input("Stack name (default: gcp_stack): ").strip() or "gcp_stack"
    d = STACKS_DIR / stack

    run(["terraform", "init"], d)
    run(["terraform", "plan"], d)

    confirm = input("Apply? (yes/no): ")
    if confirm.lower() == "yes":
        run(["terraform", "apply"], d)

if __name__ == "__main__":
    main()