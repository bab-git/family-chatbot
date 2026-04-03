# Family Chat MVP

A small local chatbot MVP for a family setup with:

- a lightweight web UI
- a local Ollama-backed chat model
- a moderation pass on both the user prompt and the assistant reply
- a stricter `child-12` profile with age-appropriate prompting and extra keyword screening
- encrypted LangGraph short-term memory stored in local SQLite
- separate persisted threads for each device profile and conversation
- a chat model selector across Llama-family options with rough local memory guidance

This MVP is designed to run on macOS first and then move cleanly to a Windows PC later.

## Architecture

The app never sends the browser directly to Ollama.

`Browser -> Family Chat server -> safety gate -> LangGraph memory lookup -> chat model -> safety gate -> LangGraph memory save`

Why this matters:

- the child profile cannot bypass moderation from the UI alone
- age-based policy lives outside the base model
- blocked child prompts and blocked replies are never written into memory
- each install keeps its own isolated local memory
- you can swap in a larger chat model later without changing the safety flow

## Default models

- Chat model: `llama3.2:1b`
- Guard model: `llama-guard3:1b`

These are the smallest practical Ollama defaults for this MVP.

## Requirements

- `uv`
- Ollama installed
- Ollama models pulled locally

## Create the local virtual environment

```bash
uv venv .venv
source .venv/bin/activate
```

On Windows later:

```powershell
uv venv .venv
.venv\Scripts\Activate.ps1
```

## Pull the models

```bash
ollama pull llama3.2:1b
ollama pull llama-guard3:1b
```

You can also pull additional Llama chat models from the app UI after the server starts.

## Configure the local device and encryption key

Copy the sample env file and set a local key:

```bash
cp .env.example .env
```

Important values:

```bash
LANGGRAPH_AES_KEY=0123456789abcdef0123456789abcdef
FAMILY_CHAT_DEVICE_MEMBER=son
FAMILY_CHAT_ADMIN_PIN=1234
FAMILY_CHAT_MODEL_PULL_REQUIRES_PIN=1
```

Notes:

- `LANGGRAPH_AES_KEY` must be exactly 16, 24, or 32 bytes long
- `FAMILY_CHAT_DEVICE_MEMBER` fixes the identity for this install, so the browser cannot switch members
- `FAMILY_CHAT_ADMIN_PIN` is optional; if blank, the `adult` profile is available without a PIN
- `FAMILY_CHAT_MODEL_PULL_REQUIRES_PIN=1` makes model pulls use that same adult PIN
- the PIN is intentionally lightweight and not meant to be tamper-proof

Privacy note:

- this encrypts the SQLite memory contents
- if someone copies only the database file, they should not be able to read the chat contents
- if someone copies both the database file and your `.env` file, they can still decrypt it
- for now this matches the local MVP tradeoff; later you can move the key into OS-level secure storage

## Run the server

Start Ollama in one terminal:

```bash
ollama serve
```

Then start the app server in another:

```bash
.venv/bin/python -m family_chat.server
```

Open:

- [http://127.0.0.1:8080](http://127.0.0.1:8080)

## Environment variables

You can customize the MVP with these optional environment variables:

```bash
export FAMILY_CHAT_OLLAMA_URL="http://127.0.0.1:11434"
export FAMILY_CHAT_CHAT_MODEL="llama3.2:1b"
export FAMILY_CHAT_GUARD_MODEL="llama-guard3:1b"
export LANGGRAPH_AES_KEY="0123456789abcdef0123456789abcdef"
export FAMILY_CHAT_DB_PATH="data/family_chat_memory.sqlite3"
export FAMILY_CHAT_MEMBERS="son,parent-a,parent-b"
export FAMILY_CHAT_DEVICE_MEMBER="son"
export FAMILY_CHAT_HOST="127.0.0.1"
export FAMILY_CHAT_PORT="8080"
export FAMILY_CHAT_ADMIN_PIN="1234"
export FAMILY_CHAT_MODEL_PULL_REQUIRES_PIN="1"
```

Notes:

- `FAMILY_CHAT_DEVICE_MEMBER` must be one of the configured `FAMILY_CHAT_MEMBERS`
- if `FAMILY_CHAT_DEVICE_MEMBER` is omitted, the app uses the first valid entry from `FAMILY_CHAT_MEMBERS`
- if `FAMILY_CHAT_MEMBERS` cannot be parsed, the app falls back to `son`
- if `FAMILY_CHAT_MODEL_PULL_REQUIRES_PIN=1` and `FAMILY_CHAT_ADMIN_PIN` is set, pulling models requires that same PIN

## Mock mode

If you want to test the UI and server without Ollama first:

```bash
export FAMILY_CHAT_MOCK_OLLAMA="1"
.venv/bin/python -m family_chat.server
```

Mock mode simulates:

- clean prompts
- blocked child prompts for explicit unsafe content
- safe assistant answers
- encrypted LangGraph persistence still works locally

## Memory behavior

This MVP now uses:

- LangGraph short-term memory
- SQLite checkpoints on local disk
- AES encryption via `LANGGRAPH_AES_KEY`
- separate threads for the configured device member, profile, and conversation

Current safety rules around memory:

- blocked child prompts are not saved
- blocked assistant replies are not saved
- only safe completed turns are persisted
- the UI can reload previous saved history for the current profile
- `New Chat` starts a fresh conversation thread for the current profile
- the sidebar shows recent saved chats for the current profile
- clicking a saved chat resumes that exact LangGraph thread
- the pre-existing ongoing conversation remains the `default` thread unless you switch to a new one

## Model selection

The UI now shows Llama-family chat models with:

- whether the model is installed locally in Ollama
- the model download size
- a rough unified/GPU memory estimate
- context window and modality info where known

Notes:

- installed models come from your local Ollama `/api/tags`
- the full selector also includes a built-in catalog of common official Ollama Llama models
- if you select a model that is not installed yet, the UI offers a `Pull model` button with live pull progress
- if you select a model that is already installed, the UI offers a `Delete model` button to remove it locally
- the memory hint is approximate, not a guarantee

The estimate is an engineering approximation based on current Ollama model sizes and common local-runtime overhead. Real needs vary by quantization, context length, and whether the machine uses discrete VRAM or shared unified memory.

## Safety behavior

The `child-12` profile applies:

- age-appropriate system prompting
- prompt moderation with `llama-guard3:1b`
- response moderation with `llama-guard3:1b`
- extra keyword blocking for explicit sexual, graphic violence, drug, hate, and self-harm language

If content is blocked, the child sees a short refusal and a suggestion to ask a parent or trusted adult.

Important: this is a practical MVP, not a perfect child-safety guarantee. For a younger child on their own machine, a separate child-focused install is still safer than relying only on a PIN to hide adult mode.

## Run tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Windows move later

When you move this to your son's Windows PC:

1. Install Ollama for Windows.
2. Pull the same two models first.
3. Install `uv`.
4. Create the venv with `uv venv .venv`.
5. Create a local `.env` based on `.env.example` and set `LANGGRAPH_AES_KEY`.
6. Set `FAMILY_CHAT_DEVICE_MEMBER` for that device.
7. Run `.\.venv\Scripts\python -m family_chat.server`.
8. If you want the PC to serve other devices on your home network, set:

```bash
set FAMILY_CHAT_HOST=0.0.0.0
.\.venv\Scripts\python -m family_chat.server
```
