# KIF Realty — Production Server Guide

Stack: **Ubuntu · Nginx · Gunicorn · PostgreSQL · Redis · Celery (worker + beat) · Django 4.2**

This describes the live server **as it actually runs** (checked Sep 2026). Sections 1–5
are day-to-day operations; section 7 is for building a new server from scratch.

> ⚠️ The X-OPP partner API only accepts whitelisted IPs. On a new server, give the X-OPP
> administrator its **public IP** first — otherwise every catalog request returns 401.

---

## 1. Server layout

| What | Where / name |
|---|---|
| App (git checkout) | `/home/ubuntu/Kif-Reality` — owned by `ubuntu` |
| Virtualenv | `/home/ubuntu/Kif-Reality/venv` |
| Secrets & settings | `/home/ubuntu/Kif-Reality/.env` (never committed) |
| Collected static files | `/home/ubuntu/Kif-Reality/staticfiles/` |
| Database | PostgreSQL, database `kif_db` |
| Django cache | `DatabaseCache`, table `sitemap_cache_table` (holds the X-OPP catalog) |
| Web app service | `gunicorn.service` |
| Catalog refresh | cron, every 30 min: `manage.py refresh_xopp` → `~/refresh_xopp.log` |
| Background jobs service | `celery.service` — worker (inquiry emails) + beat (`-B`, currently no scheduled tasks) |
| Beat schedule file | `/home/ubuntu/celerybeat-schedule` (outside the repo) |
| Nginx gzip settings | `/etc/nginx/nginx.conf` (`http` block) |
| Backups | `/home/ubuntu/backups/` |

**Run every git and `manage.py` command as `ubuntu` — never with `sudo -u www-data`.**
The folder belongs to `ubuntu`, so git refuses other users ("detected dubious ownership").
Do not add a `safe.directory` exception; just drop the `sudo`.

`kifrealty-celery.service` also exists but is **disabled on purpose** — it was a duplicate
Celery service. Leave it disabled, and don't start Celery by hand in a terminal either:
exactly one Celery service must run.

## 2. Deploying an update

Changes go to GitHub `main` first (work happens on a branch, e.g. `sinan`, then merged).
Then, on the server:

```bash
cd ~/Kif-Reality
git status                                   # must show no modified code files (see §6)
git pull --no-rebase --no-edit origin main   # the server has its own commits, so this merges
venv/bin/pip install -r requirements.txt     # only if requirements.txt changed
venv/bin/python manage.py migrate --no-input # only if models changed
venv/bin/python manage.py collectstatic --no-input
venv/bin/python manage.py check              # must end with no ERRORS (the ckeditor W001 warning is known)
sudo systemctl restart gunicorn.service celery.service
```

- **`collectstatic` is required on every deploy that touches CSS/JS or templates.** Static
  files are minified and given content-hashed names (`blogs.30523ede038e.js`, see
  `kif_realty/storage.py`); pages link to the hashed names, which exist only after
  `collectstatic`. If the site suddenly looks unstyled, this step was skipped.
- A template-only change needs just the pull and `sudo systemctl restart gunicorn.service`.
- Restart `celery.service` whenever Python code changes, so the worker runs the new code.

### Before a risky deploy — make a restore point

```bash
cd ~/Kif-Reality
git branch -f backup-before-deploy        # code restore point
```

Rollback:

```bash
git reset --hard backup-before-deploy
venv/bin/python manage.py collectstatic --no-input
sudo systemctl restart gunicorn.service celery.service
```

### Before editing data in bulk (e.g. a content-fixing management command)

```bash
venv/bin/python manage.py dumpdata main.BlogPost --indent 1 -o ~/backups/blogposts_$(date +%F).json
# restore:  venv/bin/python manage.py loaddata ~/backups/blogposts_<date>.json
```

## 3. Health checks

```bash
systemctl status gunicorn.service celery.service --no-pager      # both "active (running)"
systemctl is-enabled kifrealty-celery.service                    # must say "disabled"
ps aux | grep "[c]elery" | grep -o "celery .*" | sort | uniq -c  # only "worker -B ... -s /home/ubuntu/celerybeat-schedule" lines
tail -5 ~/refresh_xopp.log                                       # latest run ends "X-OPP caches warm"
grep -c FAILED ~/refresh_xopp.log                                # should stay 0
crontab -l | grep -c refresh_xopp                                # exactly 1 line

# X-OPP catalog loaded (≈4,000 properties). 0 = cold cache, see §5.
venv/bin/python manage.py shell -c "from main.xopp_service import get_catalog; print(len(get_catalog(cached_only=True)))" 2>/dev/null
```

From anywhere:

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://kifrealty.com/                  # 200
curl -s -o /dev/null -w "%{http_code}\n" https://kifrealty.com/properties/all/   # 200 (503 = catalog cache cold)
curl -sI -H "Accept-Encoding: gzip" \
  "https://kifrealty.com$(curl -s https://kifrealty.com/ | grep -oE '/static/css/index-styles\.[0-9a-f]+\.css' | head -1)" \
  | grep -i content-encoding                                                     # gzip
```

## 4. Nginx

Gzip for CSS/JS/JSON is switched on in the `http` block of `/etc/nginx/nginx.conf`
(Nginx's default compresses HTML only):

```nginx
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
```

The site's `server {}` block lives in `/etc/nginx/sites-enabled/` — check the exact file with
`ls /etc/nginx/sites-enabled/`. `/static/` is served straight from
`/home/ubuntu/Kif-Reality/staticfiles/` with a one-year `immutable` cache, which is safe
only because static file names are content-hashed.

After any Nginx edit, always test before reloading:

```bash
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak   # restore point
sudo nginx -t && sudo systemctl reload nginx              # reload only if the test passes
```

Restore the `.bak` only if `nginx -t` **fails**.

## 5. X-OPP catalog, sitemap and SEO pages

- The catalog is refreshed **every 30 minutes by one cron job** (the only refresh source):
  ```
  */30 * * * * cd $HOME/Kif-Reality && venv/bin/python manage.py refresh_xopp >> $HOME/refresh_xopp.log 2>&1
  ```
  A failed run keeps serving the previous catalog, and a 7-day backup copy protects listings
  during longer X-OPP outages.
- `CELERY_BEAT_SCHEDULE` in `settings.py` is intentionally empty. Never schedule the refresh
  in both cron and Celery — simultaneous runs hit the partner API's rate limit (429).
- Web requests never call X-OPP for the catalog — they read the cache. If the cache is cold
  (new server, cache table cleared), load it once by hand:
  ```bash
  venv/bin/python manage.py refresh_xopp_cache
  ```
- The property sitemap (`/sitemap-properties.xml?p=N`) and the A–Z index
  (`/properties/all/`) are both built from that cached catalog, with the same URL
  scheme as the property pages (`main.xopp_service.property_path`).
- `/property/<slug>-<id>/`: a wrong slug 301-redirects to the right one; a property
  X-OPP reports as gone returns **404**; an X-OPP outage returns **503**.
- After changes to URLs or the sitemap, resubmit `https://kifrealty.com/sitemap.xml` in
  Google Search Console.

## 6. Troubleshooting

| Message | Cause and fix |
|---|---|
| `fatal: detected dubious ownership` | A git command was run with `sudo`/as another user. Run it as `ubuntu`, without `sudo`. |
| `Need to specify how to reconcile divergent branches` | Use `git pull --no-rebase --no-edit origin main` (the server has local commits). |
| `CONFLICT (content)` during pull | `git merge --abort` puts everything back. Check `git diff <file>`, resolve, then `git add <file>` and `git commit --no-edit`. |
| `Already up to date` but the new code isn't there | The branch wasn't merged into `main` on GitHub yet. |
| Site unstyled after deploy | `collectstatic` wasn't run — run it and restart gunicorn. |
| `Unknown command` for a new `manage.py` command | The pull didn't bring the new code (see the line above), or gunicorn/celery weren't restarted. |
| `/properties/all/` returns 503 | Catalog cache is cold — `venv/bin/python manage.py refresh_xopp_cache`. |

### Known quirks of this server's checkout

The server's `main` carries its own commits (production edits to `kif_realty/settings.py`,
plus `db.sqlite3.bak`, `settings.py.save`, `staticfiles/` and `celerybeat-schedule`). That is
why pulls create merge commits. So:

- **Never `git push` from the server** — it would publish the database copy and settings.
- Never `git reset --hard origin/main` on the server — it would wipe the production settings.
- Planned cleanup: move the production settings into `.env`, untrack `staticfiles/`,
  `celerybeat-schedule` and the backup files, so deploys become a plain fast-forward pull.

## 7. Building a new server (reference)

```bash
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential nginx redis-server postgresql git
sudo systemctl enable --now redis-server postgresql

cd ~
git clone https://github.com/DelemonTech/Kif-Reality.git
cd Kif-Reality
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Create the PostgreSQL database and user, then `~/Kif-Reality/.env` (never commit it):

```env
SECRET_KEY=<generate: venv/bin/python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DEBUG=False

MICROSERVICE_API=https://microservice.x-opp.com/api
MEDIA_BASE_URL=https://microservice.x-opp.com

XOPP_API_BASE=https://www.x-opperp.com/api/v1/partner
XOPP_API_KEY=<your xopp_ key>

CELERY_BROKER_URL=redis://localhost:6379/0
```

Point the `DATABASES` setting at the new PostgreSQL database, then:

```bash
venv/bin/python manage.py makemigrations main exclusive_properties   # migrations are not committed
venv/bin/python manage.py migrate --no-input
venv/bin/python manage.py createcachetable
venv/bin/python manage.py collectstatic --no-input
venv/bin/python manage.py refresh_xopp_cache
```

Create the two systemd services. Copy the live server's Gunicorn unit
(`systemctl cat gunicorn.service` there) so the bind address matches the Nginx
`proxy_pass`. The Celery unit, as it runs today:

```ini
# /etc/systemd/system/celery.service
[Unit]
Description=Celery worker + beat for Kif Realty (X-OPP catalog refresh)
After=network.target redis-server.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/Kif-Reality
ExecStart=/home/ubuntu/Kif-Reality/venv/bin/celery -A kif_realty worker -B \
  --loglevel=info --concurrency=2 \
  -s /home/ubuntu/celerybeat-schedule
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn.service celery.service
```

Schedule the catalog refresh (`crontab -e` as `ubuntu`) — the only refresh source:

```
*/30 * * * * cd $HOME/Kif-Reality && venv/bin/python manage.py refresh_xopp >> $HOME/refresh_xopp.log 2>&1
```

Nginx: add the gzip lines from §4, and a site `server {}` block that proxies to Gunicorn and
serves `/static/` from `~/Kif-Reality/staticfiles/` and `/media/` from `~/Kif-Reality/media/`.
Then HTTPS:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d kifrealty.com -d www.kifrealty.com
```
