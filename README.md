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
4. [Running the Services](#running-the-services)
   - [Data Service](#data-service)
   - [Reversion Service](#reversion-service)
   - [Momentum Service](#momentum-service)
5. [Environment Variables](#environment-variables)
6. [Security](#security)
7. [Testing](#testing)
8. [Contributing](#contributing)
9. [License](#license)

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
