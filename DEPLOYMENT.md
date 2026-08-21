# KIF Realty — Linux Production Server Setup

Stack: **Ubuntu 22.04+ · Nginx · Gunicorn · Redis · Celery (worker + beat) · Django 4.2**

> ⚠️ Before anything: give the X-OPP administrator your **server's public IP** so it is
> whitelisted for the partner API key — otherwise every catalog request returns 401.

---

## 1. System packages

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential nginx redis-server git
sudo systemctl enable --now redis-server
```

## 2. Application setup

```bash
sudo mkdir -p /srv/kifrealty && sudo chown $USER /srv/kifrealty
cd /srv/kifrealty
git clone https://github.com/DelemonTech/Kif-Reality.git app
cd app

python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Create `/srv/kifrealty/app/.env` (never commit this file):

```env
SECRET_KEY=<generate: venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False

MICROSERVICE_API=https://microservice.x-opp.com/api
MEDIA_BASE_URL=https://microservice.x-opp.com

XOPP_API_BASE=https://www.x-opperp.com/api/v1/partner
XOPP_API_KEY=<your xopp_ key>

CELERY_BROKER_URL=redis://localhost:6379/0
```

Initialize the database, cache table, and static files:

```bash
venv/bin/python manage.py migrate --no-input
venv/bin/python manage.py createcachetable
venv/bin/python manage.py collectstatic --no-input
venv/bin/python manage.py refresh_xopp_cache   # warm the X-OPP caches once
```

## 3. Gunicorn (systemd)

`/etc/systemd/system/kifrealty.service`:

```ini
[Unit]
Description=KIF Realty Django (gunicorn)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/kifrealty/app
ExecStart=/srv/kifrealty/app/venv/bin/gunicorn kif_realty.wsgi:application \
    --bind 127.0.0.1:8001 --workers 3 --timeout 60
Restart=always

[Install]
WantedBy=multi-user.target
```

## 4. Celery worker + beat (systemd)

`/etc/systemd/system/kifrealty-celery.service`:

```ini
[Unit]
Description=KIF Realty Celery worker
After=network.target redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/kifrealty/app
ExecStart=/srv/kifrealty/app/venv/bin/celery -A kif_realty worker --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/kifrealty-beat.service` (schedules the **midnight X-OPP refresh**, Asia/Dubai time):

```ini
[Unit]
Description=KIF Realty Celery beat scheduler
After=network.target redis-server.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/srv/kifrealty/app
ExecStart=/srv/kifrealty/app/venv/bin/celery -A kif_realty beat --loglevel=info \
    --schedule /srv/kifrealty/celerybeat-schedule
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable everything:

```bash
sudo chown -R www-data:www-data /srv/kifrealty
sudo systemctl daemon-reload
sudo systemctl enable --now kifrealty kifrealty-celery kifrealty-beat
```

## 5. Nginx

`/etc/nginx/sites-available/kifrealty`:

```nginx
server {
    listen 80;
    server_name kifrealty.com www.kifrealty.com;

    client_max_body_size 20M;

    location /static/ {
        alias /srv/kifrealty/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /srv/kifrealty/app/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/kifrealty /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## 6. HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d kifrealty.com -d www.kifrealty.com
```

## 7. Deploying updates

```bash
cd /srv/kifrealty/app
sudo -u www-data git pull
sudo -u www-data venv/bin/pip install -r requirements.txt
sudo -u www-data venv/bin/python manage.py migrate --no-input
sudo -u www-data venv/bin/python manage.py collectstatic --no-input
sudo systemctl restart kifrealty kifrealty-celery kifrealty-beat
```

## 8. Health checks

```bash
systemctl status kifrealty kifrealty-celery kifrealty-beat   # all three green
journalctl -u kifrealty-beat -n 20                            # beat scheduling the nightly task
venv/bin/python manage.py refresh_xopp_cache                  # manual cache refresh any time
curl -s localhost:8001/api/developers/ | head -c 200          # API responding
```

Notes:
- The database is SQLite (`db.sqlite3`) — fine to start; switch to the commented
  PostgreSQL block in `settings.py` (psycopg2 is already installed) when traffic grows.
- The nightly job (`main.tasks.refresh_xopp_cache`) retries 3× at 10-minute intervals
  if the X-OPP API is briefly down; the 7-day catalog backup protects listings meanwhile.
- Migrations are gitignored in this repo, so run `makemigrations` on the server once
  before `migrate` if the `main`/`exclusive_properties` tables don't exist yet.
