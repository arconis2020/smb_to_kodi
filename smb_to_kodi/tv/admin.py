"""Control available admin features for the tv app."""
from django.contrib import admin

from .models import Episode, Series, Library

admin.site.register(Library)
admin.site.register(Series)
admin.site.register(Episode)
