import sys
import subprocess

from core.intent_router import route_intent
from agents.terraform_agent import generate_terraform

DEFAULT_STACK = "gcp_stack"


# ---------------------------------
# Ops runner
# ---------------------------------
def run_ops(command: str, stack: str):
    subprocess.run(
        [sys.executable, "-m", "agents.ops_agent", command, stack],
        check=True,
    )


# ---------------------------------
# Shared handler (CLI + Web)
# ---------------------------------
def handle_request(user_input: str) -> str:
    intent = route_intent(user_input)

    if intent != "terraform":
        return "Only terraform requests are supported."

    generate_terraform(user_input, stack_name=DEFAULT_STACK)

    return f"Terraform generated at terraform/stacks/{DEFAULT_STACK}"


# ---------------------------------
# CLI entrypoint
# ---------------------------------
def main():
    print("ADK started. Type your request (type 'exit' to quit).")

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break

        try:
            result = handle_request(user_input)
            print("\nResult:", result)

            # Ask for init / plan / apply (CLI only)
            if input("\nRun terraform init? (yes/no): ").lower() == "yes":
                run_ops("init", DEFAULT_STACK)

            if input("Run terraform plan? (yes/no): ").lower() == "yes":
                run_ops("plan", DEFAULT_STACK)

            if input("Run terraform apply? (yes/no): ").lower() == "yes":
                run_ops("apply", DEFAULT_STACK)

            if input("Destroy resources? (yes/no): ").lower() == "yes":
                confirm = input("Type DESTROY to confirm: ")
                if confirm == "DESTROY":
                    run_ops("destroy", DEFAULT_STACK)

        except Exception as e:
            print("\nERROR:", e)


# ---------------------------------
# Required for python -m
# ---------------------------------
if __name__ == "__main__":
    main()