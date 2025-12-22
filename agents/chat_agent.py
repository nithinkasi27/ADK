from langchain_core.messages import SystemMessage, HumanMessage

class ChatAgent:
    def __init__(self, llm, system="You are a helpful assistant."):
        self.llm = llm
        self.system = system

    def run(self, prompt: str) -> str:
        resp = self.llm.invoke([
            SystemMessage(content=self.system),
            HumanMessage(content=prompt),
        ])
        return getattr(resp, "content", "").strip()