# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do NOT** open a public GitHub issue for security vulnerabilities
2. Send an email to the repository maintainers with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Initial Assessment**: Within 7 days
- **Resolution Timeline**: Depends on severity, typically 30-90 days
- **Disclosure**: Coordinated disclosure after fix is available

### Scope

Security issues we are interested in:

- Authentication/authorization bypasses
- SQL injection, XSS, CSRF vulnerabilities
- Remote code execution
- Sensitive data exposure
- Denial of service vulnerabilities
- Insecure dependencies

### Out of Scope

- Issues in dependencies without a working exploit
- Theoretical vulnerabilities without proof of concept
- Issues requiring physical access
- Social engineering attacks

## Security Best Practices

When contributing to this project:

1. Never commit sensitive data (API keys, passwords, tokens)
2. Use environment variables for configuration
3. Follow OWASP guidelines for web security
4. Keep dependencies updated
5. Review security implications of changes

## Security Measures in Place

- Input validation on all API endpoints
- Rate limiting on public endpoints
- Secure session handling
- Regular dependency updates
- Automated security scanning in CI

## Acknowledgments

We appreciate security researchers who help keep Novel Engine secure. Contributors who report valid security issues will be acknowledged (with permission) in our security advisories.
