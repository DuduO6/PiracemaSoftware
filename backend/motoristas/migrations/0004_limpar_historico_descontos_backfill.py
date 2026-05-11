from decimal import Decimal

from django.db import migrations


def limpar_historico_backfill(apps, schema_editor):
    DescontoVale = apps.get_model("motoristas", "DescontoVale")
    Vale = apps.get_model("motoristas", "Vale")

    DescontoVale.objects.all().delete()
    Vale.objects.update(valor_descontado=Decimal("0.00"))


class Migration(migrations.Migration):

    dependencies = [
        ("motoristas", "0003_descontovale"),
    ]

    operations = [
        migrations.RunPython(limpar_historico_backfill, migrations.RunPython.noop),
    ]
