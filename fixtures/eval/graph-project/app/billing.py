def save(invoice):
    return invoice


def renew(subscription):
    subscription["auto_renew"] = True
    save(subscription)
    return subscription
