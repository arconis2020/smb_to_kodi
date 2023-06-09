# Generated by Django 4.2 on 2023-06-06 21:41

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tv", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Movie",
            fields=[
                (
                    "smb_path",
                    models.CharField(max_length=200, primary_key=True, serialize=False),
                ),
                ("watched", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["smb_path"],
                "abstract": False,
            },
        ),
        migrations.AlterModelOptions(
            name="episode",
            options={"ordering": ["smb_path"]},
        ),
        migrations.AlterModelOptions(
            name="series",
            options={"ordering": ["series_name"], "verbose_name_plural": "series"},
        ),
        migrations.AddField(
            model_name="library",
            name="content_type",
            field=models.IntegerField(choices=[(0, "Series"), (1, "Movies"), (2, "Music")], default=0),
        ),
    ]
