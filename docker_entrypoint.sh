#!/bin/sh
cd $APPDIR
# First, check for migrations:
python manage.py migrate --check || python manage.py migrate
# Now run the server with gunicorn
gunicorn --bind=0.0.0.0:8001 smb_to_kodi.wsgi
