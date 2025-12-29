#!/usr/bin/env python
"""
Ops Agent: Human-in-the-loop Terraform runner for GCP.

Commands:
  init <stack>
  plan <stack>
  apply <stack>
  destroy <stack>
"""

import subprocess
import sys
import shutil
from pathlib import Path

import typer

app = typer.Typer(help="Ops Agent: run Terraform with human-in-the-loop confirmations.")

# --------------------------------------------------
# PATHS
# --------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STACKS_DIR = PROJECT_ROOT / "terraform" / "stacks"
OUTPUT_DIR = PROJECT_ROOT / "output" / "runs"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# UTILITIES
# --------------------------------------------------
def ensure_tf_installed():
    if shutil.which("terraform") is None:
        print("Terraform not found on PATH. Install Terraform first.")
        sys.exit(1)


def stack_dir(stack: str) -> Path:
    d = STACKS_DIR / stack
    if not d.exists():
        print(f"Stack '{stack}' not found at {d}")
        sys.exit(1)
    return d


def run_cmd(cmd, cwd: Path):
    """
    Runs terraform command with NO ANSI COLORS
    (required for web / Streamlit output)
    """
    print(f"$ {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output = []
    if proc.stdout:
        for line in proc.stdout:
            print(line.rstrip())
            output.append(line)

    return proc.wait(), "".join(output)


def cleanup_stack(stack: str):
    """
    Deletes local Terraform stack after successful destroy.
    """
    stack_path = STACKS_DIR / stack
    planfile = OUTPUT_DIR / f"{stack}.tfplan"

    if planfile.exists():
        planfile.unlink()

    if stack_path.exists():
        shutil.rmtree(stack_path)

    print(f"Local Terraform stack '{stack}' removed.")


# --------------------------------------------------
# COMMANDS
# --------------------------------------------------
@app.command()
def init(stack: str):
    ensure_tf_installed()
    d = stack_dir(stack)

    rc, _ = run_cmd(
        ["terraform", "init", "-no-color"],
        d,
    )
    if rc != 0:
        sys.exit(rc)


@app.command()
def plan(stack: str):
    ensure_tf_installed()
    d = stack_dir(stack)
    planfile = OUTPUT_DIR / f"{stack}.tfplan"

    rc, _ = run_cmd(
        ["terraform", "plan", "-no-color", "-out", str(planfile)],
        d,
    )
    if rc != 0:
        sys.exit(rc)

    print(f"Plan saved: {planfile}")


@app.command()
def apply(stack: str):
    ensure_tf_installed()
    d = stack_dir(stack)
    planfile = OUTPUT_DIR / f"{stack}.tfplan"

    if planfile.exists():
        rc, _ = run_cmd(
            ["terraform", "apply", "-no-color", str(planfile)],
            d,
        )
    else:
        rc, _ = run_cmd(
            ["terraform", "apply", "-no-color"],
            d,
        )

    if rc != 0:
        sys.exit(rc)


@app.command()
def destroy(stack: str):
    """
    Destroy all resources and delete local Terraform stack.
    """
    ensure_tf_installed()
    d = stack_dir(stack)

    rc, _ = run_cmd(
        ["terraform", "destroy", "-no-color", "-auto-approve"],
        d,
    )

    if rc != 0:
        print("Terraform destroy failed. Stack preserved.")
        sys.exit(rc)

    cleanup_stack(stack)


# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    app()