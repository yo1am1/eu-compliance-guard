def newsletter(user, body):
    unsubscribe_link = "https://example.invalid/unsubscribe?u=" + user["id"]
    return body + "\n\nUnsubscribe: " + unsubscribe_link
