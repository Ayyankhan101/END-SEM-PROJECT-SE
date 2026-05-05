# Getting Started with DockWatch

## Overview

DockWatch is a powerful Docker monitoring and management tool. This guide will help you get from zero to a running dashboard.

## Prerequisites

- **Docker & Docker Compose**: Ensure they are installed on your host system.
- **Node.js 18+ and npm 9+**: Required only for local frontend development.

## Quick Start

The easiest way to start DockWatch is using the provided scripts:

1.  **Clone the repository** and enter the project folder.
2.  **Start all services**:
    ```bash
    ./start.sh
    ```
    This script automatically creates a `.env` file, generates a secure JWT secret, builds the container images, and starts the services.

## First Access

Once the containers are running:

1.  **Dashboard**: Open [http://localhost:3001](http://localhost:3001) in your web browser.
2.  **Login Credentials**:
    - **Username**: `admin`
    - **Password**: `admin123`
    > **Note**: Default credentials are for development. In production, the password is randomized - check `docker compose logs backend` for the generated password.

## Local Development

If you're modifying the code, you can run services separately.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DOCKWATCH_JWT_SECRET="your-secret-key"
export DOCKWATCH_ENCRYPTION_KEY="your-encryption-key"
python -m app.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will run at [http://localhost:5173](http://localhost:5173).
