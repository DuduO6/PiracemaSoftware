from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mdfe", "0003_manifesto_cache_xml_snapshot")]

    operations = [
        migrations.AddField(
            model_name="manifesto",
            name="xml_assinatura_conteudo_validada",
            field=models.BooleanField(default=False),
        ),
    ]
