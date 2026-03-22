from django import forms

from .constants import (
    DEFAULT_QUANTIDADE_EIXOS,
    DEFAULT_PESO_ESTIMADO_TONELADAS,
    DEFAULT_TIPO_CARGA,
    DEFAULT_PERCENTUAL_LUCRO_ADICIONAL,
    TIPOS_CARGA,
)


class FreteCalculatorForm(forms.Form):
    cidade_origem = forms.CharField(required=True, max_length=120)
    estado_origem = forms.CharField(required=False, max_length=2)
    cidade_destino = forms.CharField(required=True, max_length=120)
    estado_destino = forms.CharField(required=False, max_length=2)
    quantidade_eixos = forms.IntegerField(required=False, min_value=1, initial=DEFAULT_QUANTIDADE_EIXOS)
    tipo_carga = forms.ChoiceField(required=False, choices=TIPOS_CARGA, initial=DEFAULT_TIPO_CARGA)
    composicao_veicular = forms.BooleanField(required=False)
    alto_desempenho = forms.BooleanField(required=False)
    retorno_vazio = forms.BooleanField(required=False)
    adicionar_lucro_adicional = forms.BooleanField(required=False)
    percentual_lucro_adicional = forms.DecimalField(required=False, min_value=0, initial=DEFAULT_PERCENTUAL_LUCRO_ADICIONAL)
    peso_estimado_toneladas = forms.DecimalField(required=False, min_value=0, initial=DEFAULT_PESO_ESTIMADO_TONELADAS)
