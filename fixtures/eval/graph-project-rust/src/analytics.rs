// FICTIONAL FIXTURE — SYNTHETIC EXAMPLE ONLY
use reqwest::blocking::Client;

pub fn track(event: &str, email: &str) {
    send_event(event, email);
}

fn send_event(event: &str, email: &str) {
    let body = format!(r#"{{"event": "{}", "user": "{}"}}"#, event, email);
    Client::new().post("https://collector.example.invalid").body(body).send().ok();
}
