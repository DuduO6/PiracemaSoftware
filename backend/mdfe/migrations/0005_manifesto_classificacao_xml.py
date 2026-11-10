from django.db import migrations, models


def classificar_xmls_existentes(apps, schema_editor):
    Manifesto = apps.get_model("mdfe", "Manifesto")
    Manifesto.objects.filter(
        xml_status="DISPONIVEL",
        xml_assinatura_conteudo_validada=True,
    ).update(xml_classificacao="VERIFICADO")
    Manifesto.objects.filter(
        xml_status="DISPONIVEL",
        xml_assinatura_conteudo_validada=False,
    ).update(xml_classificacao="INFORMATIVO")


class Migration(migrations.Migration):
    dependencies = [("mdfe", "0004_manifesto_validacao_assinatura_xml")]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="xml_classificacao",
            field=models.CharField(
                choices=[
                    ("NAO_AVALIADO", "Não avaliado"),
                    ("VERIFICADO", "Conteúdo verificado"),
                    ("INFORMATIVO", "Somente informativo"),
                ],
                default="NAO_AVALIADO",
                max_length=12,
            ),
        ),
        migrations.RunPython(classificar_xmls_existentes, migrations.RunPython.noop),
    ]
