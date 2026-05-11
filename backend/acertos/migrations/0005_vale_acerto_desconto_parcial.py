from decimal import Decimal

from django.db import migrations, models


def preencher_snapshots_vales(apps, schema_editor):
    ValeAcerto = apps.get_model("acertos", "ValeAcerto")
    for vale_acerto in ValeAcerto.objects.select_related("vale"):
        valor_original = getattr(vale_acerto.vale, "valor_original", None) or vale_acerto.valor
        ValeAcerto.objects.filter(pk=vale_acerto.pk).update(
            valor_original=valor_original,
            valor_restante=Decimal("0.00"),
            quitado=True,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("motoristas", "0002_vale_valor_original_vale_valor_descontado"),
        ("acertos", "0004_desconto_cte_evidente"),
    ]

    operations = [
        migrations.AddField(
            model_name="valeacerto",
            name="valor_original",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="valeacerto",
            name="valor_restante",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="valeacerto",
            name="quitado",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(preencher_snapshots_vales, migrations.RunPython.noop),
    ]
