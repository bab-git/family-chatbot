# Changelog

All notable changes to this project will be documented in this file.

This project is still experimental, so the changelog is intentionally lightweight for now.

## [Unreleased]

### Added

- README keyword tags for better repo scanning
- this changelog for public project history

## [0.1.1] - 2026-04-06

### Added

- Windows launcher scripts for one-time setup, one-click app start, and optional startup-folder auto launch
- clearer Windows quick-use flow so a child can run the app without manually starting Ollama or the Python server

### Changed

- refreshed setup guidance across Windows and Linux/macOS around `uv sync`, local `.env` creation, and everyday app startup
- aligned the repo documentation with the simpler local-device deployment model and child-focused startup flow

### Fixed

- avoided the PowerShell `$Host` variable collision in the Windows runtime helper scripts
- suppressed the Windows PowerShell `Invoke-WebRequest` script-parsing confirmation prompt in the launcher health checks

## [0.1.0] - 2026-04-04

### Added

- local web UI served by a small Python server
- local Ollama-backed chat flow
- Llama Guard-based prompt and response moderation
- `child-12` and `adult` profiles with profile-based policy behavior
- encrypted LangGraph short-term memory stored in local SQLite
- separate persisted threads per device profile and conversation
- model selector with local install state, pull progress, and delete support
- contribution guide, MIT license, screenshot asset, and GitHub Actions test workflow

### Changed

- reframed the repository as an experimental local-first project instead of a parent-ready safety tool
- tightened the default setup to stay local-first and keep the adult profile disabled until an admin PIN is configured
- improved README onboarding with a shorter quickstart, explicit limits, and collaboration roadmap

### Security

- removed tracked local env backup material from `main` history
- ignored local env backup files to reduce the chance of accidental recommits
