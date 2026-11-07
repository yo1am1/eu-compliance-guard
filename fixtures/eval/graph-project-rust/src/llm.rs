// FICTIONAL FIXTURE — SYNTHETIC EXAMPLE ONLY
use async_openai::Client;

pub fn ask_model(prompt: &str) -> String {
    let client = Client::new();
    client.complete(prompt)
}
