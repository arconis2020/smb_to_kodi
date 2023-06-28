# Generated by Django 4.2 on 2023-06-26 22:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tv", "0005_remove_movie_watched_movie_last_watched"),
    ]

    operations = [
        migrations.CreateModel(
            name="Song",
            fields=[
                (
                    "smb_path",
                    models.CharField(max_length=200, primary_key=True, serialize=False),
                ),
                (
                    "library",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="tv.library"),
                ),
            ],
            options={
                "ordering": ["smb_path"],
                "abstract": False,
            },
        ),
    ]