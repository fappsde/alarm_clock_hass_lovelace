# Contributing to Alarm Clock Card

Thank you for your interest in contributing to the Alarm Clock Card for Home Assistant!

## Development Setup

### Prerequisites
- Node.js 18 or higher
- npm

### Installation

1. Clone the repository:
```bash
git clone https://github.com/fappsde/alarm_clock_card.git
cd alarm_clock_card
```

2. Install dependencies:
```bash
npm install
```

## Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

## Code Quality

Before submitting a PR, ensure your code passes all quality checks:

```bash
# Run linter
npm run lint

# Check version consistency
npm run check-versions
```

## Development Workflow

1. Make changes to `alarm-clock-card.js`
2. Run tests to ensure nothing breaks
3. Test manually in Home Assistant:
   - Copy the file to your HA `www/` folder
   - Clear browser cache (Ctrl+Shift+R)
   - Verify the card works as expected

## Version Management

Version is managed in:
- `package.json` - NPM package version
- `alarm-clock-card.js` - CARD_VERSION constant

The release workflow automatically updates both when a tag is pushed.

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
- Update version in package.json
- Update CARD_VERSION in alarm-clock-card.js
- Generate changelog from commits
- Create a GitHub release with the card file

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks
5. Test in Home Assistant
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### PR Guidelines

- Write clear, descriptive commit messages
- Include tests for new features
- Update documentation as needed
- Follow the existing code style
- Keep PRs focused on a single feature/fix
- Include screenshots for UI changes

## Code Style

- Use ES6+ JavaScript features
- Follow Lit element best practices
- Use proper ES module imports (don't access HA internals directly)
- Avoid circular references
- Add duplicate registration protection for custom elements

## Testing in Home Assistant

To test your changes:

1. Copy `alarm-clock-card.js` to your Home Assistant `www/` folder
2. Add/update the resource in Lovelace:
```yaml
lovelace:
  resources:
    - url: /local/alarm-clock-card.js
      type: module
```
3. Clear browser cache (Ctrl+Shift+R)
4. Add the card to a dashboard
5. Test all functionality

## Code Review

All submissions require review. We aim to review PRs within a few days.

## Questions?

Feel free to open an issue for questions or discussion!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
