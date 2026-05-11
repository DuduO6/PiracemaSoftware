from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


CASAS_DECIMAIS = Decimal("0.01")
FATOR_DESCONTO_CTE = Decimal("0.10")


def arredondar(valor):
    return (valor or Decimal("0.00")).quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)


def calcular_descontos_cte(apps, schema_editor):
    Acerto = apps.get_model("acertos", "Acerto")
    ItemAcerto = apps.get_model("acertos", "ItemAcerto")

    for item in ItemAcerto.objects.all():
        valor_desconto_cte = Decimal("0.00")
        if item.teve_cte:
            valor_desconto_cte = arredondar(item.peso * item.valor_tonelada * FATOR_DESCONTO_CTE)

        ItemAcerto.objects.filter(pk=item.pk).update(valor_desconto_cte=valor_desconto_cte)

    for acerto in Acerto.objects.all():
        desconto_cte = arredondar(
            sum(
                (
                    item.valor_desconto_cte
                    for item in ItemAcerto.objects.filter(acerto=acerto, teve_cte=True)
                ),
                Decimal("0.00"),
            )
        )
        Acerto.objects.filter(pk=acerto.pk).update(desconto_cte=desconto_cte)


class Migration(migrations.Migration):

    dependencies = [
        ("acertos", "0003_cte_totais_acerto"),
    ]

    operations = [
        migrations.AddField(
            model_name="acerto",
            name="desconto_cte",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="itemacerto",
            name="valor_desconto_cte",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.RunPython(calcular_descontos_cte, migrations.RunPython.noop),
    ]
