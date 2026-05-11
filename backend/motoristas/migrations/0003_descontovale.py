from django.db import migrations, models
import django.db.models.deletion


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
    ]
