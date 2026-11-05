def subscribe(plan):
    return {"plan": plan, "auto_renew": True, "renewal_period_days": 365}


def cancel(subscription):
    subscription["auto_renew"] = False
    return subscription
