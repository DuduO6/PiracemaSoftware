from django.db import migrations, models


def preencher_valor_original(apps, schema_editor):
    Vale = apps.get_model("motoristas", "Vale")
    for vale in Vale.objects.all():
        Vale.objects.filter(pk=vale.pk).update(
            valor_original=vale.valor,
            valor_descontado=0,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("motoristas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vale",
            name="valor_original",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="vale",
            name="valor_descontado",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.RunPython(preencher_valor_original, migrations.RunPython.noop),
    ]
