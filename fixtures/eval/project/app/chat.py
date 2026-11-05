def coach(user, llm):
    prompt = "Plan meals for weight " + str(user["weight_kg"])
    return llm.complete(prompt)
