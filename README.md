# Odoo-Telegram Bot

A Telegram bot for searching and viewing Odoo Purchase Requests.

## Setup

1.  **Configure Environment**:
    Copy `.env.example` to `.env` and fill in your details:
    ```bash
    cp .env.example .env
    ```
    -   `TELEGRAM_BOT_TOKEN`: Get from @BotFather
    -   `ODOO_URL`: Your Odoo instance URL
    -   `ENCRYPTION_KEY`: Generate a 32-byte base64 key (e.g. using `cryptography.fernet.Fernet.generate_key()`)

2.  **Run with Docker**:
    ```bash
    docker-compose up --build -d
    ```

3.  **Local Development**:
    ```bash
    pip install -r requirements.txt
    python src/main.py
    ```
    *(Ensure Redis is running locally or update REDIS_URL)*

## Usage

-   `/start` - Connect to Odoo
-   `/find <keywords>` - Search PRs (e.g. `/find laptop`)
-   `/view_<id>` - View PR details
-   `/logout` - Disconnect

## Features
-   Secure credential storage (AES-256)
-   Redis-backed sessions
-   Pagination
-   Deep linking to Odoo
