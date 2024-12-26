# Contributing to MCP Server Neurolorap

We love your input! We want to make contributing to MCP Server Neurolorap as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the style guidelines
6. Issue that pull request!

## Pull Request Process

1. Update the README.md and PROJECT_SUMMARY.md with details of changes to the interface
2. Update the tests to cover your changes
3. The PR will be merged once you have the sign-off of at least one maintainer

## Any Contributions You Make Will Be Under the MIT License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project. Feel free to contact the maintainers if that's a concern.

## Report Bugs Using GitHub's [Issue Tracker](https://github.com/aindreyway/mcp-server-neurolorap/issues)

We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/aindreyway/mcp-server-neurolorap/issues/new).

## Write Bug Reports with Detail, Background, and Sample Code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Give sample code if you can
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

## Use a Consistent Coding Style

- Use [Black](https://github.com/psf/black) for Python code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide
- Add type hints to all functions and classes
- Write docstrings for all public functions and classes
- Keep line length to 79 characters
- Use meaningful variable names

## Code Review Process

The core team looks at Pull Requests on a regular basis. After feedback has been given we expect responses within two weeks. After two weeks we may close the pull request if it isn't showing any activity.

## Community

Discussions about the project take place on this repository's [Issues](https://github.com/aindreyway/mcp-server-neurolorap/issues) and [Pull Requests](https://github.com/aindreyway/mcp-server-neurolorap/pulls) sections. Anybody is welcome to join these conversations.

## Testing

We use pytest for testing. Before submitting a pull request, please ensure that:

1. All existing tests pass
2. New tests are added for new functionality
3. Code coverage remains above 80%

To run tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server_neurolorap

# Run specific test categories
pytest -m unit          # Unit tests
pytest -m integration   # Integration tests
```

## Documentation

- Keep README.md and PROJECT_SUMMARY.md up to date
- Document all new features
- Update docstrings for any modified functions
- Add type hints for all new code

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/aindreyway/mcp-server-neurolorap/tags).

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

## References

This document was adapted from the open-source contribution guidelines for [Facebook's Draft](https://github.com/facebook/draft-js/blob/a9316a723f9e918afde44dea68b5f9f39b7d9b00/CONTRIBUTING.md).
