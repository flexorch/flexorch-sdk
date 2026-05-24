# Contributing

Thank you for your interest in contributing to flexorch-sdk.

## Setup

```bash
git clone https://github.com/flexorch/flexorch-sdk
cd flexorch-sdk
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

Tests use [respx](https://lundberg.github.io/respx/) to mock httpx — no network calls or API key required.

## Code style

- Line length: 100 characters (`ruff` configured in `pyproject.toml`)
- Type hints required on all public functions
- No `any` in public interfaces — use explicit types

```bash
pip install ruff
ruff check src/ tests/
```

## Submitting changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Add tests for new behaviour
4. Open a pull request against `main`

## Reporting issues

Open an issue at [github.com/flexorch/flexorch-sdk/issues](https://github.com/flexorch/flexorch-sdk/issues).

For security issues, email [privacy@flexorch.com](mailto:privacy@flexorch.com) instead of opening a public issue.
