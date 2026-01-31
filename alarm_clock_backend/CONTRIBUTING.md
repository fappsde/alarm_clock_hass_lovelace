# Contributing to Alarm Clock Backend

Thank you for your interest in contributing to the Alarm Clock backend integration for Home Assistant!

## Development Setup

### Prerequisites
- Python 3.11 or higher
- Home Assistant development environment (optional, for testing)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/fappsde/alarm_clock_backend.git
cd alarm_clock_backend
```

2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_coordinator.py

# Run with coverage
pytest tests/ --cov=custom_components/alarm_clock --cov-report=term-missing
```

## Code Quality

Before submitting a PR, ensure your code passes all quality checks:

```bash
# Run linter
ruff check custom_components/

# Format code
black custom_components/

# Sort imports
isort custom_components/
```

## Version Management

Version is managed in `custom_components/alarm_clock/manifest.json`. The release workflow automatically updates this when a tag is pushed.

## Creating a Release

Releases are automated via GitHub Actions:

1. Update CHANGELOG.md with release notes
2. Commit changes
3. Create and push a tag:
```bash
git tag v1.0.10
git push origin v1.0.10
```

The workflow will automatically:
- Update the version in manifest.json
- Create alarm_clock.zip
- Generate changelog from commits
- Create a GitHub release

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### PR Guidelines

- Write clear, descriptive commit messages
- Include tests for new features
- Update documentation as needed
- Follow the existing code style
- Keep PRs focused on a single feature/fix

## Code Review

All submissions require review. We aim to review PRs within a few days.

## Questions?

Feel free to open an issue for questions or discussion!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
