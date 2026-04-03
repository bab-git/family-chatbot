# Changelog

All notable changes to this project will be documented in this file.

This project is still experimental, so the changelog is intentionally lightweight for now.

## [Unreleased]

### Added

- README keyword tags for better repo scanning
- this changelog for public project history

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
