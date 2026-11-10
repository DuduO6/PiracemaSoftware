from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("mdfe", "0001_initial"),
        ("motoristas", "0004_limpar_historico_descontos_backfill"),
    ]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="xml_importado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="xml_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.CreateModel(
            name="ManifestoCondutor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_xml", models.CharField(max_length=150)),
                ("cpf", models.CharField(max_length=11)),
                ("importado_em", models.DateTimeField(auto_now_add=True)),
                (
                    "manifesto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="condutores",
                        to="mdfe.manifesto",
                    ),
                ),
                (
                    "motorista",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="manifestos_mdfe",
                        to="motoristas.motorista",
                    ),
                ),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.AddConstraint(
            model_name="manifestocondutor",
            constraint=models.UniqueConstraint(
                fields=("manifesto", "cpf"), name="mdfe_condutor_manifesto_cpf_unico"
            ),
        ),
    ]
