// FICTIONAL FIXTURE — SYNTHETIC EXAMPLE ONLY
pub mod plans;

pub struct Subscription { pub renews_automatically: bool }

impl Subscription {
    pub fn renew(&self) -> bool { plans::price_for("monthly") > 0 }
}
