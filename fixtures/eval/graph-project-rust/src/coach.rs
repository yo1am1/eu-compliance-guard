// FICTIONAL FIXTURE — SYNTHETIC EXAMPLE ONLY
use crate::llm::ask_model;
use crate::models::{load_member, Member};

pub fn plan_meals(db: &Db, member_id: u64) -> String {
    let member: Member = load_member(db, member_id);
    ask_model(&format!("Plan meals for weight {}", member.weight_kg))
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn plans() { plan_meals(&fake_db(), 1); }
}
