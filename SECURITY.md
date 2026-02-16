# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

Only the latest release is actively supported with security updates. Users are encouraged to upgrade promptly.

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in scanipy, please report it responsibly:

1. **Email:** Send a detailed report to the maintainer via [GitHub private vulnerability reporting](https://github.com/papadoxie/scanipy/security/advisories/new).
2. **Include:**
   - A description of the vulnerability and its potential impact.
   - Steps to reproduce (proof of concept if possible).
   - The affected component(s) — e.g., CLI (`scanipy.py`), API services (`services/`), integrations (`integrations/`), analysis tools (`tools/`), or infrastructure (`terraform/`).
   - Your suggested fix, if any.

### What to Expect

- **Acknowledgement** within **48 hours** of your report.
- An initial **assessment and severity classification** within **5 business days**.
- A **fix or mitigation plan** communicated to you before any public disclosure.
- Credit in the advisory (unless you prefer to remain anonymous).

### Disclosure Policy

We follow [coordinated vulnerability disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure). We ask that you:

- Allow us a reasonable window (typically **90 days**) to address the issue before public disclosure.
- Do not exploit the vulnerability beyond what is necessary to demonstrate it.
- Do not access, modify, or delete data belonging to other users.

## Scope

The following components are **in scope** for security reports:

| Component | Path / Location | Examples |
| --- | --- | --- |
| **CLI Interface** | `scanipy.py` | Command injection, argument parsing flaws |
| **Data Models** | `models.py` | Data validation bypasses |
| **GitHub Integrations** | `integrations/` | Token leakage, API credential exposure, SSRF |
| **Analysis Tools** | `tools/` | Arbitrary code execution via semgrep/codeql configs |
| **API Services** | `services/` | Authentication/authorization flaws, SQL injection, API abuse |
| **Database** | `services/db/` | SQL injection, connection string exposure, data leakage |
| **Infrastructure** | `terraform/` | Misconfigured IAM roles, public S3 buckets, insecure ECS task definitions |
| **Dependencies** | `requirements.txt`, `pyproject.toml` | Vulnerable transitive dependencies |

The following are **out of scope**:

- Vulnerabilities in upstream tools (semgrep, codeql) themselves — please report those to their respective maintainers.
- Social engineering attacks against maintainers or users.
- Denial of service attacks that require excessive resources.

## Security Best Practices for Contributors

### Secrets & Credentials

- **Never** commit secrets, API tokens, AWS credentials, or database passwords to the repository.
- Use environment variables or AWS Secrets Manager for all sensitive configuration.
- All AWS credentials must be managed via IAM roles attached to ECS tasks, not hardcoded.

### Database Security

- **PostgreSQL only** — no SQLite or dual-path code.
- Always use parameterized queries (`%s` placeholders via psycopg2). **Never** use string formatting or concatenation for SQL.
- Database connections must use TLS/SSL when communicating with RDS.
- Use connection retry with exponential backoff (handled by `BaseDatabase`).

### API & Network Security

- All API services must enforce authentication and authorization.
- API endpoints must validate and sanitize all input.
- HTTPS is required for all external communication.
- No localhost fallbacks for API URLs in production.

### Infrastructure Security

- Terraform state files must be stored in encrypted S3 backends, never committed to the repository.
- ECS tasks must follow the principle of least privilege for IAM roles.
- S3 buckets for analysis results must not be publicly accessible.
- Use Terraform workspaces (`dev`/`prod`) to isolate environments.

### Dependency Management

- Regularly audit dependencies with `pip-audit` or equivalent.
- Pin dependency versions in `requirements.txt`.
- Review dependency updates for security advisories before upgrading.

## Security-Related Configuration

### Environment Variables

The following environment variables contain sensitive data and must be handled securely:

| Variable | Purpose | Storage Recommendation |
| --- | --- | --- |
| `GITHUB_TOKEN` | GitHub API authentication | AWS Secrets Manager / env var |
| `DATABASE_URL` | PostgreSQL connection string | AWS Secrets Manager |
| `AWS_*` credentials | AWS service access | IAM roles (preferred) or env var |

### Network Policies

- ECS tasks should run in private subnets with NAT gateway access.
- RDS instances must not be publicly accessible.
- Security groups should follow least-privilege access patterns.

## Known Security Considerations

- **Analysis tool execution:** scanipy runs third-party analysis tools (semgrep, codeql) on cloned repositories. Repositories are cloned into temporary directories that are cleaned up after analysis. Malicious repositories could potentially exploit vulnerabilities in these tools.
- **GitHub API tokens:** Tokens used for GitHub API access have access to the scopes granted by the user. Use fine-grained personal access tokens with minimal required permissions.

## References

- [GitHub Security Advisories](https://github.com/papadoxie/scanipy/security/advisories)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS ECS Security Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/security.html)
