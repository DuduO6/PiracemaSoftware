from rest_framework import serializers


MOTORISTA_NAO_ENCONTRADO = (
    "Motorista não encontrado no cadastro. Selecione um motorista cadastrado para continuar."
)


def validar_motorista_autorizado(motorista, usuario):
    if motorista is None:
        raise serializers.ValidationError({"motorista": MOTORISTA_NAO_ENCONTRADO})
    if motorista.usuario_id != usuario.id:
        raise serializers.ValidationError(
            {"motorista": "O motorista selecionado não pertence ao seu cadastro autorizado."}
        )
    return motorista


def salvar_viagem_validada(serializer, usuario):
    motorista = serializer.validated_data.get(
        "motorista",
        getattr(serializer.instance, "motorista", None),
    )
    validar_motorista_autorizado(motorista, usuario)
    if serializer.instance:
        return serializer.save()
    return serializer.save(usuario=usuario)
