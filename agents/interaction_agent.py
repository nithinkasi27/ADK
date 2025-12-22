from core.intent_router import route_intent
from agents.terraform_agent import generate_terraform
from agents.chat_agent import ChatAgent
from core.llm import get_llm

def main():
    llm = get_llm()
    chat = ChatAgent(llm)

    while True:
        user = input("You: ").strip()
        if user.lower() in {"exit", "quit"}:
            break

        intent = route_intent(user)

        if intent == "terraform":
            generate_terraform(user)
        else:
            print(chat.run(user))

if __name__ == "__main__":
    main()