from app import storage


def track(event, visitor_id):
    send_to_analytics(event, visitor_id)
    storage.save({"event": event})


def send_to_analytics(event, visitor_id):
    return {"tracking": event, "cookie": visitor_id}
