// FICTIONAL FIXTURE — SYNTHETIC EXAMPLE ONLY
pub struct Member {
    pub member_id: u64,
    pub weight_kg: f32,
    pub birth_date: String,
}

pub fn load_member(db: &Db, member_id: u64) -> Member {
    let row = db.fetch_member(member_id);
    Member { member_id, weight_kg: row.get("weight_kg"), birth_date: row.get("birth_date") }
}
