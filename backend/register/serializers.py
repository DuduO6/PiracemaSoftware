from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
import re

User = get_user_model()


def normalize_cnpj(value):
    if value in (None, ""):
        return None

    normalized = re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()
    if not re.fullmatch(r"[A-Z0-9]{12}[0-9]{2}", normalized):
        raise serializers.ValidationError("Informe um CNPJ válido com 14 posições.")

    if normalized.isdigit():
        if len(set(normalized)) == 1:
            raise serializers.ValidationError("Informe um CNPJ válido.")
        digits = [int(char) for char in normalized]
        for size, weights in (
            (12, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
            (13, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]),
        ):
            remainder = sum(digit * weight for digit, weight in zip(digits[:size], weights)) % 11
            expected = 0 if remainder < 2 else 11 - remainder
            if digits[size] != expected:
                raise serializers.ValidationError("Os dígitos verificadores do CNPJ são inválidos.")
    return normalized


def validate_unique_cnpj(value, instance=None):
    normalized = normalize_cnpj(value)
    if normalized is None:
        return None
    queryset = User.objects.filter(cnpj=normalized)
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise serializers.ValidationError("Este CNPJ já está cadastrado em outra conta.")
    return normalized

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    cnpj = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=18)

    class Meta:
        model = User
        fields = ['username', 'email', 'cnpj', 'password']

    def validate_cnpj(self, value):
        return validate_unique_cnpj(value)

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            cnpj=validated_data.get('cnpj'),
            password=validated_data['password']
        )
        return user


class UserAccountSerializer(serializers.ModelSerializer):
    cnpj = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=18)
    username = serializers.CharField(required=False, max_length=150)
    senha_atual = serializers.CharField(required=False, write_only=True, trim_whitespace=False)
    nova_senha = serializers.CharField(required=False, write_only=True, trim_whitespace=False)
    confirmar_nova_senha = serializers.CharField(required=False, write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'cnpj', 'senha_atual', 'nova_senha', 'confirmar_nova_senha'
        ]
        read_only_fields = ['id', 'email']

    def validate_cnpj(self, value):
        return validate_unique_cnpj(value, self.instance)

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Informe o nome de usuário.")
        queryset = User.objects.filter(username__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Este nome de usuário já está em uso.")
        return value

    def validate(self, attrs):
        current_username = self.instance.username if self.instance else ""
        username_changed = "username" in attrs and attrs["username"] != current_username
        password_changed = bool(attrs.get("nova_senha"))

        if attrs.get("confirmar_nova_senha") and not password_changed:
            raise serializers.ValidationError({"nova_senha": "Informe a nova senha."})

        if username_changed or password_changed:
            current_password = attrs.get("senha_atual")
            if not current_password:
                raise serializers.ValidationError(
                    {"senha_atual": "Informe sua senha atual para alterar o nome de usuário ou a senha."}
                )
            if not self.instance.check_password(current_password):
                raise serializers.ValidationError({"senha_atual": "A senha atual está incorreta."})

        if password_changed:
            if attrs.get("confirmar_nova_senha") != attrs["nova_senha"]:
                raise serializers.ValidationError({"confirmar_nova_senha": "As novas senhas não coincidem."})
            try:
                validate_password(attrs["nova_senha"], user=self.instance)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"nova_senha": list(exc.messages)}) from exc

        return attrs

    def update(self, instance, validated_data):
        new_password = validated_data.pop("nova_senha", None)
        validated_data.pop("senha_atual", None)
        validated_data.pop("confirmar_nova_senha", None)
        instance = super().update(instance, validated_data)
        if new_password:
            instance.set_password(new_password)
            instance.save(update_fields=("password",))
        return instance
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
