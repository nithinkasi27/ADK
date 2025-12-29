import streamlit as st
import subprocess
import sys
from pathlib import Path

# ---------------------------------
# Paths
# ---------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STACK_NAME = "gcp_stack"
STACK_DIR = PROJECT_ROOT / "terraform" / "stacks" / STACK_NAME

# ---------------------------------
# Page config
# ---------------------------------
st.set_page_config(
    page_title="ADK Terraform Agent",
    layout="wide",
)

st.title("ADK – Terraform Agent (Human-in-the-loop)")

st.markdown(
    """
This UI controls **real Terraform execution**.

Nothing runs unless **you explicitly click a button**.
"""
)

# ---------------------------------
# User Input
# ---------------------------------
user_input = st.text_area(
    "Infrastructure Request",
    placeholder="Example: Create a VM instance in GCP with name test-vm",
    height=120,
)

# ---------------------------------
# 1️⃣ Generate Terraform
# ---------------------------------
if st.button("1️⃣ Generate Terraform"):
    if not user_input.strip():
        st.error("Please enter an infrastructure request.")
    else:
        st.info("Generating Terraform code...")

        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from agents.interaction_agent import handle_request;"
                    f"print(handle_request({user_input!r}))"
                ),
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            st.error(proc.stderr)
        else:
            st.success("Terraform generated successfully")
            st.code(proc.stdout)

# ---------------------------------
# Show Generated Terraform Files
# ---------------------------------
if STACK_DIR.exists():
    st.subheader("📂 Generated Terraform Files")

    for tf_file in sorted(STACK_DIR.rglob("*.tf")):
        st.markdown(f"**{tf_file.relative_to(STACK_DIR)}**")
        st.code(tf_file.read_text(), language="hcl")

# ---------------------------------
# 2️⃣ Terraform INIT
# ---------------------------------
st.subheader("2️⃣ Terraform Init")

if st.button("Run terraform init"):
    st.info("Running terraform init...")

    proc = subprocess.run(
        [sys.executable, "-m", "agents.ops_agent", "init", STACK_NAME],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        st.error(proc.stderr)
    else:
        st.success("Terraform init completed")
        st.code(proc.stdout)

# ---------------------------------
# 3️⃣ Terraform PLAN
# ---------------------------------
st.subheader("3️⃣ Terraform Plan")

if st.button("Run terraform plan"):
    st.info("Running terraform plan...")

    proc = subprocess.run(
        [sys.executable, "-m", "agents.ops_agent", "plan", STACK_NAME],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        st.error(proc.stderr)
    else:
        st.success("Terraform plan completed")
        st.code(proc.stdout)

# ---------------------------------
# 4️⃣ Terraform APPLY
# ---------------------------------
st.subheader("4️⃣ Terraform Apply")

apply_confirm = st.checkbox(
    "I understand this will CREATE real resources in my GCP account"
)

if st.button("Apply Terraform"):
    if not apply_confirm:
        st.error("Please confirm before applying.")
    else:
        st.warning("Applying Terraform. This may take a few minutes.")

        proc = subprocess.run(
            [sys.executable, "-m", "agents.ops_agent", "apply", STACK_NAME],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            st.error(proc.stderr)
        else:
            st.success("Terraform apply completed")
            st.code(proc.stdout)

# ---------------------------------
# 5️⃣ Terraform DESTROY
# ---------------------------------
st.subheader("5️⃣ Terraform Destroy")

destroy_confirm = st.checkbox(
    "I understand this will DESTROY all resources created by this stack"
)

destroy_text = st.text_input("Type DESTROY to confirm")

if st.button("Destroy Terraform"):
    if not destroy_confirm or destroy_text != "DESTROY":
        st.error("Destroy not confirmed.")
    else:
        st.warning("Destroying Terraform resources...")

        proc = subprocess.run(
            [sys.executable, "-m", "agents.ops_agent", "destroy", STACK_NAME],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )

        if proc.returncode != 0:
            st.error(proc.stderr)
        else:
            st.success("Resources destroyed and stack cleaned up")
            st.code(proc.stdout)