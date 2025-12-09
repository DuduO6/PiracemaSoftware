from rest_framework import serializers
from .models import Caminhao, Carreta
import json

class CarretaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carreta
        fields = ["id", "placa", "renavam", "crlv"]


class CaminhaoSerializer(serializers.ModelSerializer):
    carretas = CarretaSerializer(many=True, read_only=True)

    class Meta:
        model = Caminhao
        fields = "__all__"
        extra_kwargs = {
            "nome_conjunto": {"required": False},
            "placa_cavalo": {"required": False},
            "renavam_cavalo": {"required": False},
            "marca_modelo": {"required": False},
        }

    def create(self, validated_data):
        request = self.context["request"]

        # cria caminhão sem extrair nada do PDF
        caminhao = Caminhao.objects.create(**validated_data)

        # recebe carretas se houver
        carretas_json = json.loads(request.data.get("carretas", "[]"))

        for idx, c in enumerate(carretas_json):
            crlv_file = request.FILES.get(f"crlv_carreta_{idx}")

            Carreta.objects.create(
                caminhao=caminhao,
                placa=c.get("placa"),
                renavam=c.get("renavam"),
                crlv=crlv_file
            )

        return caminhao


