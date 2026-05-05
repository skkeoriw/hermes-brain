# New Machine Runbook

1. Install git, curl, and python3.
2. Clone the private repository:

```bash
git clone https://github.com/ChangfengHU/hermes-brain.git
cd hermes-brain
```

3. Run bootstrap:

```bash
bash scripts/bootstrap_new_machine.sh
```

4. Verify:

```bash
hermes doctor
hermes skills list
hermes
```

5. If this machine should run gateway/webhook services:

```bash
hermes gateway install
hermes gateway start
hermes gateway status
```

6. If this machine only needs CLI Hermes, do not start gateway.
