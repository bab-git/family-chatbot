# Contributing

Thanks for taking a look at this experiment.

The project goal is to explore safer local-first family chat patterns without over-claiming what the current system can do. Small improvements are welcome, especially when they make the repo easier to understand, safer to evaluate, or easier to run locally.

## Good places to help

- strengthen safety tests and adversarial cases
- improve refusal behavior for risky topics
- add more age profiles or clearer parent-only controls
- improve setup ergonomics on macOS and Windows
- tighten documentation, screenshots, and repo onboarding

## Local setup

```bash
uv sync
cp .env.example .env
```

Set a local `LANGGRAPH_AES_KEY` in `.env`, then run either:

```bash
export FAMILY_CHAT_MOCK_OLLAMA=1
.venv/bin/python -m family_chat.server
```

or the full Ollama-backed flow after pulling the default models.

## Before opening a PR

- keep changes local-first and easy to review
- avoid language that overstates child-safety guarantees
- add or update tests when behavior changes
- run:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Pull request guidance

- describe the user-visible change clearly
- call out any safety tradeoffs or new assumptions
- keep scope focused when possible

If you want to make a large change, opening an issue or discussion first is helpful.
