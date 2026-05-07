# Contributing to GeoData Security System

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Development Setup

1. Fork the repository
2. Clone your fork
3. Follow the [Quick Start](README.md#quick-start) guide in the README

## Code Style

### Python (Backend)
- We use [Ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Run `ruff check .` and `ruff format .` before committing
- Follow PEP 8 conventions

### JavaScript/Vue (Frontend)
- We use [ESLint](https://eslint.org/) for linting
- Run `npm run lint` before committing
- Use Composition API (`<script setup>`) for Vue components

## Commit Messages

Use clear, descriptive commit messages:

```
feat: add batch approval endpoint
fix: resolve token refresh race condition
docs: update API documentation
refactor: extract watermark logic into separate module
test: add unit tests for auth endpoints
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests if applicable
4. Ensure all linting passes
5. Update documentation if needed
6. Submit a pull request

## Reporting Issues

- Use GitHub Issues for bug reports
- Include steps to reproduce
- Include error messages and screenshots
- Specify your environment (OS, Python version, Node version)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
