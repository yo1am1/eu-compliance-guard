ENCRYPTION = "aes-256-gcm"
LOG_RETENTION_DAYS = 30


def save(blob, key):
    return encrypt(blob, key, ENCRYPTION)


def purge_old_logs(logs, today):
    return [entry for entry in logs if (today - entry.created).days <= LOG_RETENTION_DAYS]
