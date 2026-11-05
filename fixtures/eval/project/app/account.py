def delete_account(db, user_id):
    db.erase_user_records(user_id)
    db.erase_uploaded_photos(user_id)


def export_data(db, user_id):
    return db.dump_user_records(user_id, format="json")
