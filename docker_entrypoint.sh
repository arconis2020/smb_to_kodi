#!/bin/sh
cd $APPDIR
# First, check for migrations:
python manage.py migrate --check || python manage.py migrate
# Now run the server with gunicorn
gunicorn --bind=0.0.0.0:8001 --threads=10 smb_to_kodi.wsgi &
while true; do
    python manage.py syncdisk  # Sync all series.
    sleep 900  # Wait 15 minutes between sync runs.
done
