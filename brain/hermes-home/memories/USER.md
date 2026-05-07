User prefers API/webhook examples as complete copy-paste requests suitable for Postman, without requiring shell variables or dynamic signature generation.
§
User wants Hermes deployments across multiple machines to share accumulated “brain” state (memories, skills, webhook/SOP automations, and useful history) so new machines do not start from scratch, while still keeping machine-specific runtime/config local where appropriate.
§
User wants a private GitHub repository named around “Hermes 大脑” / `hermes-brain` to sync all Hermes persistent data across machines, and for testing accepts plaintext synchronization of secrets/keys rather than encryption.
§
User prefers one-shot automation via Hermes/Copilot and wants reusable copy-paste master prompts/templates so each new wiki can be bootstrapped end-to-end (repo + Actions + webhook + Telegram + multi-wiki routing) in a single chat.
§
User expects Hermes troubleshooting/recommendations to be based on the machine’s current live configuration first (e.g., currently connected model/provider), not generic model suggestions.
§
User prefers concise Chinese troubleshooting with binary conclusions first; focus on raw-change and KG-impact outcomes. For incremental no-raw-change runs, do not send Telegram; when sending, include quantitative KG deltas (counts + named entities/relations).