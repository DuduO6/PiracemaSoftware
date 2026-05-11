from django.db import migrations, models
import django.db.models.deletion


def criar_historico_descontos_existentes(apps, schema_editor):
    DescontoVale = apps.get_model("motoristas", "DescontoVale")
    ValeAcerto = apps.get_model("acertos", "ValeAcerto")

    for vale_acerto in ValeAcerto.objects.select_related("vale", "acerto"):
        if not vale_acerto.vale_id or not vale_acerto.valor:
            continue

        DescontoVale.objects.create(
            vale=vale_acerto.vale,
            acerto=vale_acerto.acerto,
            valor=vale_acerto.valor,
            saldo_antes=vale_acerto.valor_original,
            saldo_depois=vale_acerto.valor_restante,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("acertos", "0005_vale_acerto_desconto_parcial"),
        ("motoristas", "0002_vale_valor_original_vale_valor_descontado"),
    ]

    operations = [
        migrations.CreateModel(
            name="DescontoVale",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.DateTimeField(auto_now_add=True)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=10)),
                ("saldo_antes", models.DecimalField(decimal_places=2, max_digits=10)),
                ("saldo_depois", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "acerto",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="descontos_vales",
                        to="acertos.acerto",
                    ),
                ),
                (
                    "vale",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="descontos",
                        to="motoristas.vale",
                    ),
                ),
            ],
            options={
                "ordering": ["-data"],
            },
        ),
        migrations.RunPython(criar_historico_descontos_existentes, migrations.RunPython.noop),
    ]
