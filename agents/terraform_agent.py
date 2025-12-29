import json
import os
import re
from pathlib import Path
from typing import Dict

from core.paths import STACKS_DIR
from core.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

# =========================================================
# LLM
# =========================================================
LLM = get_llm()

# =========================================================
# SYSTEM PROMPT (HARD CONTRACT)
# =========================================================
SYSTEM_PROMPT = """
You are a senior Terraform engineer for GCP.

Return ONLY a valid JSON object.
NO markdown. NO backticks. NO explanations.

HARD RULES (VIOLATION = BUG):
- DO NOT include terraform {} blocks
- DO NOT include provider blocks
- DO NOT define variables named project_id or region
- DO NOT reference project_id or region anywhere
- DO NOT pass project_id or region to modules
- Modules must NEVER contain provider logic
- Every resource MUST be inside a module
- Each module MUST contain main.tf, variables.tf, outputs.tf

STACK RULES:
- Stack main.tf may ONLY wire modules together
- Stack main.tf must NOT contain project_id arguments

JSON FORMAT:

{
  "modules": [
    {
      "name": "module_name",
      "files": {
        "main.tf": "...",
        "variables.tf": "...",
        "outputs.tf": "..."
      }
    }
  ],
  "stack": {
    "main.tf": "...",
    "outputs.tf": "..."
  }
}
"""

# =========================================================
# PROJECT / REGION (STACK-ONLY)
# =========================================================
def resolve_project_and_region(user_request: str):
    proj = re.search(r"project id\s+([a-z0-9\-]+)", user_request, re.I)
    reg = re.search(r"region\s+([a-z0-9\-]+)", user_request, re.I)

    project_id = proj.group(1) if proj else os.environ.get("GOOGLE_CLOUD_PROJECT")
    region = reg.group(1) if reg else os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

    if not project_id:
        raise RuntimeError(
            "Project ID not found. Provide it in request or set GOOGLE_CLOUD_PROJECT."
        )

    return project_id, region

# =========================================================
# JSON LOADER (BULLETPROOF)
# =========================================================
def safe_json_load(raw: str) -> Dict:
    if not raw:
        raise RuntimeError("LLM returned empty output")

    for fence in ("```json", "```terraform", "```"):
        raw = raw.replace(fence, "")

    raw = raw.strip()

    start = raw.find("{")
    end = raw.rfind("}")

    if start == -1 or end == -1:
        raise RuntimeError(f"No JSON object found:\n{raw}")

    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Invalid JSON returned by LLM:\n{raw}") from e

# =========================================================
# SANITIZERS (CRITICAL)
# =========================================================
FORBIDDEN_TOKENS = (
    "project_id",
    "var.project_id",
    "region",
    "var.region",
)

def sanitize_module_hcl(hcl: str) -> str:
    """
    Removes provider blocks, terraform blocks,
    and ANY reference to project_id / region.
    """
    lines = hcl.splitlines()
    cleaned = []
    skip = False

    for line in lines:
        s = line.strip()

        # Remove terraform/provider blocks
        if s.startswith("terraform") or s.startswith("provider "):
            skip = True
            continue

        if skip:
            if s == "}":
                skip = False
            continue

        # Drop forbidden tokens completely
        if any(tok in s for tok in FORBIDDEN_TOKENS):
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def sanitize_stack_main_tf(hcl: str) -> str:
    """
    Ensures stack main.tf NEVER passes project_id / region to modules.
    """
    lines = hcl.splitlines()
    cleaned = []

    for line in lines:
        if any(tok in line for tok in FORBIDDEN_TOKENS):
            continue
        cleaned.append(line)

    return "\n".join(cleaned).strip()

# =========================================================
# MAIN ENTRY
# =========================================================
def generate_terraform(user_request: str, stack_name: str = "gcp_stack"):
    stack_dir = STACKS_DIR / stack_name
    modules_dir = stack_dir / "modules"

    stack_dir.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------
    # PROJECT / REGION → STACK ONLY
    # -----------------------------------------------------
    project_id, region = resolve_project_and_region(user_request)

    (stack_dir / "terraform.tfvars").write_text(
        f'project_id = "{project_id}"\nregion = "{region}"\n',
        encoding="utf-8",
    )

    # -----------------------------------------------------
    # STACK VARIABLES (SYSTEM OWNED)
    # -----------------------------------------------------
    (stack_dir / "variables.tf").write_text(
        """
variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}
""".strip(),
        encoding="utf-8",
    )

    # -----------------------------------------------------
    # PROVIDER (STACK ONLY)
    # -----------------------------------------------------
    (stack_dir / "providers.tf").write_text(
        """
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
""".strip(),
        encoding="utf-8",
    )

    # -----------------------------------------------------
    # LLM CALL
    # -----------------------------------------------------
    llm_json = LLM.bind(response_format={"type": "json_object"})
    resp = llm_json.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_request),
        ]
    )

    raw = getattr(resp, "content", "")
    print("\n====== RAW LLM OUTPUT ======")
    print(raw)
    print("====== END RAW LLM OUTPUT ======\n")

    data = safe_json_load(raw)

    # -----------------------------------------------------
    # WRITE MODULES (STRICTLY CLEAN)
    # -----------------------------------------------------
    for mod in data.get("modules", []):
        mod_dir = modules_dir / mod["name"]
        mod_dir.mkdir(parents=True, exist_ok=True)

        for fname, content in mod["files"].items():
            content = sanitize_module_hcl(content)
            (mod_dir / fname).write_text(content, encoding="utf-8")

    # -----------------------------------------------------
    # WRITE STACK FILES (STRICT)
    # -----------------------------------------------------
    for fname, content in data.get("stack", {}).items():
        content = sanitize_stack_main_tf(content)
        (stack_dir / fname).write_text(content, encoding="utf-8")

    print(f"Terraform stack generated successfully at: {stack_dir}")