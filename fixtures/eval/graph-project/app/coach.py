from app.models import load_member
from .llm import ask_model


def plan_meals(db, member_id):
    member = load_member(db, member_id)
    return ask_model("Plan meals for weight " + str(member.weight_kg))
