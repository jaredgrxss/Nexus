# Nexus: Algorithmic Trading Platform

Nexus is a robust and modular algorithmic trading platform designed to execute various trading strategies, such as **mean reversion** and **momentum**, in a scalable and secure manner. The platform integrates with AWS services (SQS, SNS, Secrets Manager) for message queuing, event-driven architecture, and secure secret management. It is designed to run both locally and in cloud environments.

---

## Table of Contents

1. [Features](#features)
2. [Architecture](#architecture)
3. [Getting Started](#getting-started)
   - [Prerequisites](#prerequisites)
   - [Installation](#installation)
   - [Configuration](#configuration)
4. [Environment Variables](#environment-variables)
5. [Security](#security)
6. [Testing](#testing)
7. [Contributing](#contributing)
8. [License](#license)

---

## Features

- **Modular Design**: Easily add new trading strategies as independent services.
- **Event-Driven Architecture**: Uses AWS SQS and SNS for message queuing and event handling.
- **Secure Secret Management**: Integrates with AWS Secrets Manager for secure storage of sensitive information.
- **Environment Agnostic**: Runs seamlessly in both local and cloud environments.
- **Logging and Monitoring**: Built-in logging for debugging and monitoring.

---

## Architecture

The platform is structured as follows:

- **Services**: Each trading strategy (e.g., Reversion, Momentum) is implemented as a separate service.
- **Helpers**: Common utilities like logging, AWS client management, and environment decryption.
- **Environment Management**: Uses `.env` files for configuration, with support for encrypted environment files for added security.
- **AWS Integration**: Leverages AWS SQS, SNS, and Secrets Manager for message handling and secret management.

---

## Getting Started

### Prerequisites

- Python 3.12+
- AWS account with access to SQS, SNS, and Secrets Manager.
- AWS CLI configured with valid credentials.
- GPG for encrypting/decrypting environment files.

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jaredgrxss/nexus.git
cd nexus
```

2. Install dependencies:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Set up environment files:
```bash
cp .env.example .env
```

### Configuration

1. Environment Setup
```bash
nano .env
python src/helpers/cloud/encrypt_env_file .env
```

2. AWS Resources
- Create SQS queues for inter-service communication 
- Configure SNS topics for event notifications 
- Store sensitive credentials in Secrets Manager

3. GPG Setup
```bash
gpg --full-generate-key  # Create new keypair
gpg --list-secret-keys   # Note your key ID
```


## Environment Variables
Variable                         Description                         Required
`AWS_ACCESS_KEY_ID`              AWS IAM access key                  Yes
`AWS_SECRET__ACCESS_KEY`         AWS IAM secret key                  Yes
`DATA_SNS_ARN`                   ARN for market data topic           Yes
`BROKER_ACCESS_KEY`              Encrypted via secrets manager       Yes
`BROKER_SECRET_ACCESS_KEY`       Logging verbosity                   No


## Security
- **Encrypted Secrets**: Production credentials stored in AWS Secrets Manager 
- **Environment Encryption**: 
```Bash
# Decrypt for local development
python src/helpers/env_helpers.py decrypt .env.gpg
```
- **IAM Policies**: Least-privilege access for AWS resources
- **Audit Logging**: All trades logged to S3 bucket with versioning

## Testing
Run the test suite with coverage:
```bash
pytest --cov=src --cov-report=html
```

- Unit tests: `tests/unit`
- Integration/tests: `tests/integration`
- Security tests: `tests/security`

## Contributing
1. Fork the repository
2. Create your feature branch:
```bash
git checkout -b feature/new-strategy
```
3. Add tests for new features
4. Submit a pull request

## License
Distributed under the MIT License. See `LICENSE` for more information
