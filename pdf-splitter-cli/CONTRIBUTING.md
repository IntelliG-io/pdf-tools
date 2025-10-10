# Contributing to PDF Splitter CLI

Thank you for your interest in contributing to PDF Splitter CLI! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a welcoming environment

## Getting Started

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/yourusername/pdf-splitter-cli.git
   cd pdf-splitter-cli
   ```

3. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

5. **Install development dependencies:**
   ```bash
   pip install pytest pytest-cov
   ```

## Development Setup

### Project Structure

```
pdf-splitter-cli/
├── pdf_splitter/
│   ├── __init__.py       # Package initialization
│   ├── cli.py            # Command-line interface
│   ├── splitter.py       # Core PDF splitting logic
│   └── utils.py          # Utility functions
├── tests/
│   ├── test_splitter.py      # Unit tests
│   └── test_integration.py   # Integration tests
├── README.md
├── CHANGELOG.md
├── setup.py
└── requirements.txt
```

### Running the Development Version

```bash
# Run from source
python -m pdf_splitter.cli --help

# Or use the installed command
pdf-splitter --help
```

## Making Changes

### Branch Naming

- `feature/description` - New features
- `bugfix/description` - Bug fixes
- `docs/description` - Documentation updates
- `test/description` - Test additions/updates

### Commit Messages

Follow conventional commit format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/updates
- `refactor`: Code refactoring
- `style`: Code style changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(splitter): add support for PDF rotation
fix(cli): handle empty directory in batch mode
docs(readme): add troubleshooting section
test(integration): add batch processing tests
```

## Testing

### Running Tests

```bash
# Run all tests
python -m unittest discover -s tests

# Run specific test file
python -m unittest tests.test_splitter

# Run with pytest
pytest tests/

# Run with coverage
pytest tests/ --cov=pdf_splitter --cov-report=term
```

### Writing Tests

- Add unit tests for new functions in `tests/test_splitter.py`
- Add integration tests for workflows in `tests/test_integration.py`
- Ensure all tests pass before submitting
- Aim for 80%+ code coverage

**Test Example:**
```python
def test_new_feature(self):
    """Test description."""
    # Arrange
    splitter = PDFSplitter('test.pdf')
    
    # Act
    result = splitter.new_method()
    
    # Assert
    self.assertEqual(result, expected_value)
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints for function parameters and returns
- Maximum line length: 100 characters
- Use meaningful variable names

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When invalid input provided
        
    Example:
        >>> function_name("test", 5)
        True
    """
    pass
```

### Code Organization

- Keep functions focused and single-purpose
- Use meaningful names for variables and functions
- Add comments for complex logic
- Group related functionality together

## Submitting Changes

### Pull Request Process

1. **Update your fork:**
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes:**
   - Write code
   - Add tests
   - Update documentation

4. **Run tests:**
   ```bash
   python -m unittest discover -s tests
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat(scope): description"
   ```

6. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create Pull Request:**
   - Go to GitHub
   - Click "New Pull Request"
   - Fill in the template
   - Link related issues

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Code refactoring

## Testing
- [ ] All tests pass
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] No breaking changes (or documented)
```

## Areas for Contribution

### High Priority
- Password-protected PDF support
- PDF merging capabilities
- Performance optimizations
- Additional output formats

### Medium Priority
- Page rotation and manipulation
- Watermark support
- Bookmark preservation
- Enhanced metadata handling

### Documentation
- More usage examples
- Video tutorials
- API documentation
- Troubleshooting guides

### Testing
- Additional edge cases
- Performance benchmarks
- Cross-platform testing
- Integration with CI/CD

## Questions?

- Open an issue for questions
- Check existing issues and PRs
- Review documentation

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to PDF Splitter CLI! 🎉
