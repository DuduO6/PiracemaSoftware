from django.db import migrations, models


def normalizar_viagens_sem_cte(apps, schema_editor):
    Viagem = apps.get_model("viagens", "Viagem")
    Viagem.objects.filter(teve_cte=False).update(descontar_cte=False)


class Migration(migrations.Migration):
    dependencies = [("viagens", "0003_importacaomdfeviagem")]

    operations = [
        migrations.AddField(
            model_name="viagem",
            name="descontar_cte",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(normalizar_viagens_sem_cte, migrations.RunPython.noop),
    ]
