import json
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
# SYSTEM PROMPT (STRICT CONTRACT)
# =========================================================
SYSTEM_PROMPT = """
You are a senior Terraform engineer for GCP.

You MUST return a VALID JSON OBJECT.
DO NOT include markdown, comments, or explanations.

STRICT RULES (DO NOT VIOLATE):
- DO NOT define terraform {} blocks
- DO NOT define provider blocks
- DO NOT define variables named "project_id" or "region"
- DO NOT reference var.project_id or var.region
- Each resource must be inside a Terraform module
- Each module MUST contain: main.tf, variables.tf, outputs.tf

Required JSON format:

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
# SAFE JSON PARSER
# =========================================================
def _safe_json_load(text: str) -> Dict:
    if not text or not text.strip():
        raise ValueError("LLM returned empty response")

    text = text.strip()

    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)

# =========================================================
# SANITIZERS
# =========================================================
def _sanitize_hcl(lines):
    """
    Removes terraform blocks, provider blocks,
    and forbidden global variables.
    """
    cleaned = []
    skip = False

    for line in lines:
        stripped = line.strip()

        # Remove terraform/provider blocks
        if stripped.startswith("terraform") or stripped.startswith("provider "):
            skip = True
            continue

        if skip:
            if stripped == "}":
                skip = False
            continue

        # Remove forbidden globals
        if "project_id" in stripped or "region" in stripped:
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def _sanitize_variables_tf(lines):
    """
    Removes forbidden variables from variables.tf
    """
    cleaned = []
    skip = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('variable "project_id"') or stripped.startswith('variable "region"'):
            skip = True
            continue

        if skip:
            if stripped == "}":
                skip = False
            continue

        cleaned.append(line)

    return "\n".join(cleaned).strip()


def fix_multiline_hcl(content: str) -> str:
    """
    Converts unsafe multi-line values (SSH keys, scripts, certs)
    into Terraform heredoc syntax.
    """
    if not content:
        return content

    # SSH public keys
    if "ssh-rsa" in content or "ssh-ed25519" in content:
        if 'ssh_keys = "' in content:
            content = content.replace(
                'ssh_keys = "',
                'ssh_keys = <<EOT\n'
            )
            content = content.replace('"', '\nEOT', 1)

    # Startup scripts / cloud-init
    if "#!/bin/bash" in content or "startup_script" in content:
        if 'startup_script = "' in content:
            content = content.replace(
                'startup_script = "',
                'startup_script = <<EOT\n'
            )
            content = content.replace('"', '\nEOT', 1)

    return content

# =========================================================
# MAIN ENTRY
# =========================================================
def generate_terraform(user_request: str, stack_name: str = "gcp_stack"):
    stack_dir = STACKS_DIR / stack_name
    modules_dir = stack_dir / "modules"

    stack_dir.mkdir(parents=True, exist_ok=True)
    modules_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------
    # SYSTEM-OWNED VARIABLES
    # -----------------------------------------------------
    (stack_dir / "variables.tf").write_text(
        """
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}
""".strip(),
        encoding="utf-8",
    )

    # -----------------------------------------------------
    # SYSTEM-OWNED PROVIDER
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
    # LLM CALL (JSON-ONLY)
    # -----------------------------------------------------
    llm_json = LLM.bind(response_format={"type": "json_object"})

    resp = llm_json.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_request),
    ])

    raw = getattr(resp, "content", "")

    print("\n====== RAW LLM OUTPUT ======")
    print(raw)
    print("====== END RAW OUTPUT ======\n")

    data = _safe_json_load(raw)

    # -----------------------------------------------------
    # WRITE MODULES (FULL SANITIZATION)
    # -----------------------------------------------------
    for mod in data.get("modules", []):
        mod_dir = modules_dir / mod["name"]
        mod_dir.mkdir(parents=True, exist_ok=True)

        for fname, content in mod["files"].items():
            lines = content.splitlines()

            if fname == "main.tf":
                content = _sanitize_hcl(lines)
                content = fix_multiline_hcl(content)

            elif fname == "variables.tf":
                content = _sanitize_variables_tf(lines)

            elif fname == "outputs.tf":
                content = content.strip()

            (mod_dir / fname).write_text(content, encoding="utf-8")

    # -----------------------------------------------------
    # WRITE STACK FILES
    # -----------------------------------------------------
    for fname, content in data.get("stack", {}).items():
        if fname == "variables.tf":
            continue  # system owns this

        lines = content.splitlines()
        content = _sanitize_hcl(lines)
        content = fix_multiline_hcl(content)

        (stack_dir / fname).write_text(content, encoding="utf-8")

    print(f"✅ Terraform generated successfully at: {stack_dir}")