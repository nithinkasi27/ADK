def route_intent(user_input: str) -> str:
    keywords = ["terraform", "gcp", "bucket", "vpc", "subnet", "iam", "cloud"]
    return "terraform" if any(k in user_input.lower() for k in keywords) else "chat"