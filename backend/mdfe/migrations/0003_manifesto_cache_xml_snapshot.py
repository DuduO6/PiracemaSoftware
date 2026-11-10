from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mdfe", "0002_manifesto_xml_condutores")]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="xml_criptografado",
            field=models.BinaryField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="xml_status",
            field=models.CharField(
                choices=[
                    ("AUSENTE", "XML ainda não consultado"),
                    ("DISPONIVEL", "XML armazenado"),
                    ("ERRO", "Falha ao obter o XML"),
                    ("REMOVIDO", "XML removido após encerramento"),
                ],
                default="AUSENTE",
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="xml_fonte",
            field=models.CharField(
                blank=True,
                choices=[
                    ("PORTAL_NACIONAL", "Portal Nacional do MDF-e"),
                    ("IMPORTACAO_MANUAL", "Importação manual"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="xml_ultima_tentativa_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="xml_ultimo_erro",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="destinos",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="manifesto",
            name="snapshot_fiscal",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="consultamanifestos",
            name="xml_baixados",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="consultamanifestos",
            name="xml_em_cache",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="consultamanifestos",
            name="xml_erros",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
