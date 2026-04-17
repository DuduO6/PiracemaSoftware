from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("viagens", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="viagem",
            name="numero_cte",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="viagem",
            name="teve_cte",
            field=models.BooleanField(default=False),
        ),
    ]
