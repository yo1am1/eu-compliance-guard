def ask_model(prompt):
    return openai_client().complete(prompt)


def openai_client():
    raise NotImplementedError("fictional fixture")
