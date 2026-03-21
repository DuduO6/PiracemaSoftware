from django import forms


class SeguroCargasForm(forms.Form):
    origem = forms.CharField(required=True, max_length=100)
    destino = forms.CharField(required=True, max_length=100)
    valor_rctr_c = forms.DecimalField(required=True, min_value=0, decimal_places=2, max_digits=14)
    valor_rcdc = forms.DecimalField(required=True, min_value=0, decimal_places=2, max_digits=14)

    def clean(self):
        cleaned_data = super().clean()
        valor_rctr_c = cleaned_data.get("valor_rctr_c")
        valor_rcdc = cleaned_data.get("valor_rcdc")

        if valor_rctr_c is None or valor_rcdc is None:
            return cleaned_data

        if valor_rctr_c == 0 and valor_rcdc == 0:
            raise forms.ValidationError(
                "Informe ao menos um valor de carga maior que zero para realizar o cálculo."
            )

        return cleaned_data

