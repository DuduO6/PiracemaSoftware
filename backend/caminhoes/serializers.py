from rest_framework import serializers
from .models import Caminhao, Carreta
import json

class CarretaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carreta
        fields = ["id", "placa", "renavam"]


class CaminhaoSerializer(serializers.ModelSerializer):
    usuario = serializers.HiddenField(default=serializers.CurrentUserDefault())
    carretas = CarretaSerializer(many=True, read_only=True)

    class Meta:
        model = Caminhao
        fields = "__all__"

    def create(self, validated_data):
        request = self.context["request"]

        # cria caminhão
        caminhao = Caminhao.objects.create(**validated_data)

        # recebe JSON do front
        lista = json.loads(request.data.get("carretas", "[]"))

        if len(lista) == 0:
            return caminhao

        # --- PRIMEIRA PLACA = CAVALO ---
        primeiro = lista[0]
        caminhao.placa_cavalo = primeiro.get("placa")
        caminhao.renavam_cavalo = primeiro.get("renavam")
        caminhao.save()

        # --- DEMAIS = CARRETAS ---
        for item in lista[1:]:
            Carreta.objects.create(
                caminhao=caminhao,
                placa=item.get("placa"),
                renavam=item.get("renavam"),
            )

        return caminhao
