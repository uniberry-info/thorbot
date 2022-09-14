# Thor Bot

Gatekeeper bot for the Unimore Informatica unofficial Telegram group network

\[ [**Website**](https://thor.steffo.eu) | [PyPI](https://pypi.org/project/thorunimore/) \]

> NOTE: This bot will be replaced soon with its rewrite, [Loki Bot](https://github.com/Steffo99/lokiunimore). Development on this version has ceased.

![The OpenGraph image of this page, with the project logo in the foreground and a blurred version of the Thor website in the background.](resources/opengraph.png)

## Functionality

If added as an administrator to a Telegram group, this bot will instantly kick any joining member who hasn't passed verification.

Verification is performed by:

1. visiting the bot's homepage
2. pressing the "Verify" button
3. logging in via Google with a `@studenti.unimore.it` account
4. following the deep link to Telegram
5. pressing the "Start" button in the bot chat
6. answering the few questions the bot asks about the user's configuration

Additionally, verified users of the bot may choose to make their real name available for lookups via a bot command.

Verified members joining a monitored group which made their real name available are announced by the bot in the group.

## Installation via PyPI

This method is recommended only for development purposes.

1. Create a new venv and enter it:
   ```console
   $ python -m venv venv
   $ source venv/bin/activate
   ```
   
2. Download through PyPI:
   ```console
   $ pip install thorunimore
   ```
   
3. Install the packages required to connect to the desired SQL database:
   
   - For PostgreSQL:
     ```console
     $ pip install psycopg2-binary
     ```

4. Set the following environment variables:

   - [The URI of the SQL database you want to use](https://docs.sqlalchemy.org/en/13/core/engines.html)
     ```bash
     export SQLALCHEMY_DATABASE_URI="postgresql://steffo@/thor_dev"
     ```
   
   - [A Google OAuth 2.0 client id and client secret](https://console.developers.google.com/apis/credentials)
     ```bash
     export GOOGLE_CLIENT_ID="000000000000-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.apps.googleusercontent.com"
     export GOOGLE_CLIENT_SECRET="aaaaaaaaaaaaaaaaaaaaaaaa"
     ```
   
   - A random string of characters used to sign Telegram data
     ```bash
     export SECRET_KEY="Questo è proprio un bel test."
     ```
   
   - [api_id and api_hash for a Telegram application](https://my.telegram.org/apps)
     ```bash
     export TELEGRAM_API_ID="1234567"
     export TELEGRAM_API_HASH="abcdefabcdefabcdefabcdefabcdefab"
     ```

   - [The username and token of the Telegram bot](https://t.me/BotFather)
     ```bash
     export TELEGRAM_BOT_USERNAME="thorunimorebot"
     export TELEGRAM_BOT_TOKEN="1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
     ```

   - The desired logging level and format
     ```bash
     export LOG_LEVEL="DEBUG"
     export LOG_FORMAT="{asctime}\t| {name}\t| {message}"
     ```
   
   - The url at which web is hosted
     ```bash
     export BASE_URL="http://lo.steffo.eu:30008"
     ```
     
   - The url to join the Telegram group
     ```bash
     export GROUP_URL="https://t.me/joinchat/AAAAAAAAAAAAAAAAAAAAAA"
     ```

5. Run both of the project's processes simultaneously:
   ```console
   $ python -m thorunimore.telegram &
   $ python -m thorunimore.web &
   ```

### Configuring as a SystemD unit

This section assumes the project's files are located in `/opt/thorunimore`.

6. Install `gunicorn` in the previously created venv:
   ```console
   $ pip install gunicorn
   ```

7. Create the `bot-thorunimore` systemd unit by creating the `/etc/systemd/system/bot-thorunimore.service` file:
   ```ini
   [Unit]
   Name=bot-thorunimore
   Description=A moderator bot for the Unimore Informatica group
   Requires=network-online.target postgresql.service
   After=network-online.target nss-lookup.target
   
   [Service]
   Type=exec
   User=thorunimore
   WorkingDirectory=/opt/thorunimore
   ExecStart=/opt/thorunimore/venv/bin/python -OO -m thorunimore.telegram
   Environment=PYTHONUNBUFFERED=1
   
   [Install]
   WantedBy=multi-user.target
   ```

8. Create the `web-thorunimore` systemd unit by creating the `/etc/systemd/system/web-thorunimore.service` file:
   ```ini
   [Unit]
   Name=web-thorunimore
   Description=Thorunimore Gunicorn Server
   Wants=network-online.target postgresql.service
   After=network-online.target nss-lookup.target
   
   [Service]
   Type=exec
   User=thorunimore
   WorkingDirectory=/opt/thorunimore
   ExecStart=/opt/thorunimore/venv/bin/gunicorn -b 127.0.0.1:30008 thorunimore.web.__main__:reverse_proxy_app
   
   [Install]
   WantedBy=multi-user.target
   ```
   
9. Create the `/etc/systemd/system/bot-thorunimore.d/override.conf` and 
   `/etc/systemd/system/web-thorunimore.d/override.conf` containing the previously configured variables, so that they are passed to the SystemD unit:
   ```ini
   [Service]
   Environment="SQLALCHEMY_DATABASE_URI=postgresql://thorunimore@/thor_prod"
   Environment="GOOGLE_CLIENT_ID=000000000000-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.apps.googleusercontent.com"
   Environment="GOOGLE_CLIENT_SECRET=aaaaaaaaaaaaaaaaaaaaaaaa"
   Environment="SECRET_KEY=Questo è proprio un bel server."
   Environment="TELEGRAM_API_ID=1234567"
   Environment="TELEGRAM_API_HASH=abcdefabcdefabcdefabcdefabcdefab"
   Environment="TELEGRAM_BOT_USERNAME=thorunimorebot"
   Environment="TELEGRAM_BOT_TOKEN=1111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
   Environment="LOG_LEVEL=DEBUG"
   Environment="LOG_FORMAT={asctime}\t| {name}\t| {message}"
   Environment="BASE_URL=https://thor.steffo.eu"
   Environment="GROUP_URL=https://t.me/joinchat/AAAAAAAAAAAAAAAAAAAAAA"
   ```
   
10. Start (and optionally enable) both services:
    ```console
    # systemctl start "bot-thorunimore" "web-thorunimore"
    # systemctl enable "bot-thorunimore" "web-thorunimore"
    ```

11. Reverse-proxy the web service with a web server such as Apache HTTPd:
    ```apacheconf
    <VirtualHost *:80>
    
    ServerName "thor.steffo.eu"
    Redirect permanent "/" "https://thor.steffo.eu/"
    
    </VirtualHost>
    
    <VirtualHost *:443>
    
    ServerName "thor.steffo.eu"
    
    ProxyPass "/" "http://127.0.0.1:30008/"
    ProxyPassReverse "/" "http://127.0.0.1:30008/"
    RequestHeader set "X-Forwarded-Proto" expr=%{REQUEST_SCHEME}
    
    SSLEngine on
    SSLCertificateFile "/root/.acme.sh/*.steffo.eu/fullchain.cer"
    SSLCertificateKeyFile "/root/.acme.sh/*.steffo.eu/*.steffo.eu.key"
    
    </VirtualHost>
    ```
    ```console
    # a2ensite rp-thorunimore
    ```

## Installation via Docker

This method is recommended for production deployments.

- Two Docker images are provided, `thorunimore-web` and `thorunimore-telegram`, which only require configuration of the environment and setup of a reverse proxy.
