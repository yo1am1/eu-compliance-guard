class Member:
    def __init__(self, member_id, weight_kg, birth_date):
        self.member_id = member_id
        self.weight_kg = weight_kg
        self.birth_date = birth_date


def load_member(db, member_id):
    row = db.fetch_member(member_id)
    return Member(row["id"], row["weight_kg"], row["birth_date"])
