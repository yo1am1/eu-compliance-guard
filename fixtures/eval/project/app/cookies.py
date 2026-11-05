def landing(response, visitor_id):
    response.set_cookie("_analytics", visitor_id, max_age=60 * 60 * 24 * 395)
    return response
