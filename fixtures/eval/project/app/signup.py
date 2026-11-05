MINIMUM_AGE = 16


def can_register(birth_date, today, parental_consent):
    age = (today - birth_date).days // 365
    return age >= MINIMUM_AGE or parental_consent
