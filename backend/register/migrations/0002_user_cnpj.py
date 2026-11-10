from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("register", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="cnpj",
            field=models.CharField(blank=True, max_length=14, null=True, unique=True),
        ),
    ]
