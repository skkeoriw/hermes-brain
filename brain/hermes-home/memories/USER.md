User prefers API/webhook examples as complete copy-paste requests suitable for Postman, without requiring shell variables or dynamic signature generation.
§
User wants Hermes deployments across multiple machines to share accumulated “brain” state (memories, skills, webhook/SOP automations, and useful history) so new machines do not start from scratch, while still keeping machine-specific runtime/config local where appropriate.
§
User wants a private GitHub repository named around “Hermes 大脑” / `hermes-brain` to sync all Hermes persistent data across machines, and for testing accepts plaintext synchronization of secrets/keys rather than encryption.
§
User prefers Hermes brain synchronization to be agent-friendly and automation-first: give Copilot/Hermes a single initialization or sync instruction/file rather than requiring step-by-step manual commands.
§
User expects Hermes troubleshooting/recommendations to be based on the machine’s current live configuration first (e.g., currently connected model/provider), not generic model suggestions.
§
User prefers concise Chinese troubleshooting with binary conclusions first; focus on raw-change and KG-impact outcomes. For incremental no-raw-change runs, do not send Telegram; when sending, include quantitative KG deltas (counts + named entities/relations).