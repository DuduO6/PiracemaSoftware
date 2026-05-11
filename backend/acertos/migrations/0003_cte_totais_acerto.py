from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models


CASAS_DECIMAIS = Decimal("0.01")
DESCONTO_CTE = Decimal("0.90")


def arredondar(valor):
    return (valor or Decimal("0.00")).quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)


def aplicar_desconto_cte(apps, schema_editor):
    Viagem = apps.get_model("viagens", "Viagem")
    Acerto = apps.get_model("acertos", "Acerto")
    ItemAcerto = apps.get_model("acertos", "ItemAcerto")

    for viagem in Viagem.objects.all():
        valor_total = viagem.peso * viagem.valor_tonelada
        if viagem.teve_cte:
            valor_total *= DESCONTO_CTE
        Viagem.objects.filter(pk=viagem.pk).update(valor_total=arredondar(valor_total))

    for item in ItemAcerto.objects.select_related("viagem"):
        teve_cte = bool(item.viagem and item.viagem.teve_cte)
        valor_total = item.peso * item.valor_tonelada
        if teve_cte:
            valor_total *= DESCONTO_CTE
        ItemAcerto.objects.filter(pk=item.pk).update(
            teve_cte=teve_cte,
            valor_total=arredondar(valor_total),
        )

    for acerto in Acerto.objects.all():
        itens = list(ItemAcerto.objects.filter(acerto=acerto))
        itens_com_cte = [item for item in itens if item.teve_cte]
        itens_sem_cte = [item for item in itens if not item.teve_cte]

        valor_total_viagens = arredondar(sum((item.valor_total for item in itens), Decimal("0.00")))
        valor_total_viagens_com_cte = arredondar(sum((item.valor_total for item in itens_com_cte), Decimal("0.00")))
        valor_total_viagens_sem_cte = arredondar(sum((item.valor_total for item in itens_sem_cte), Decimal("0.00")))

        percentual_comissao = acerto.percentual_comissao or Decimal("13.00")
        desconto_vales = acerto.desconto_vales or Decimal("0.00")
        desconto_fixo = acerto.desconto_fixo or Decimal("0.00")
        comissao = arredondar(valor_total_viagens * (percentual_comissao / Decimal("100")))
        valor_a_receber = arredondar(comissao - desconto_vales - desconto_fixo)

        Acerto.objects.filter(pk=acerto.pk).update(
            total_viagens=len(itens),
            valor_total_viagens=valor_total_viagens,
            total_viagens_com_cte=len(itens_com_cte),
            valor_total_viagens_com_cte=valor_total_viagens_com_cte,
            total_viagens_sem_cte=len(itens_sem_cte),
            valor_total_viagens_sem_cte=valor_total_viagens_sem_cte,
            comissao=comissao,
            valor_a_receber=valor_a_receber,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("viagens", "0002_viagem_cte_fields"),
        ("acertos", "0002_acerto_desconto_fixo_acerto_desconto_vales_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="acerto",
            name="total_viagens_com_cte",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="acerto",
            name="valor_total_viagens_com_cte",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="acerto",
            name="total_viagens_sem_cte",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="acerto",
            name="valor_total_viagens_sem_cte",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10),
        ),
        migrations.AddField(
            model_name="itemacerto",
            name="teve_cte",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(aplicar_desconto_cte, migrations.RunPython.noop),
    ]
