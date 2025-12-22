from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TERRAFORM_DIR = PROJECT_ROOT / "terraform"
STACKS_DIR = TERRAFORM_DIR / "stacks"
STATE_DIR = TERRAFORM_DIR / "state"

STACKS_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)