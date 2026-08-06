from django.core.management import call_command
from django.db import migrations


def carregar_base_nacional(apps, schema_editor):
    call_command("carregar_base_nacional_logistica", verbosity=0)


class Migration(migrations.Migration):
    dependencies = [("inteligencia_logistica", "0002_categoriapolo_pracapedagio_produtologistico_and_more")]
    operations = [migrations.RunPython(carregar_base_nacional, migrations.RunPython.noop)]
