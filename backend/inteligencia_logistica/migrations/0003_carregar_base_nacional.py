from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("inteligencia_logistica", "0002_categoriapolo_pracapedagio_produtologistico_and_more")]
    # A carga pertencia à funcionalidade removida de Inteligência Logística.
    # Mantemos o nó histórico para instalações existentes e novas.
    operations = []
