from django.contrib import admin
from django.utils import timezone
from .models import CategoriaDespesa, Despesa, FuncionarioDespesa

@admin.register(CategoriaDespesa)
class CategoriaDespesaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'usuario', 'cor')
    list_filter = ('usuario', 'nome')
    search_fields = ('nome', 'descricao')

class DespesaInline(admin.TabularInline):
    model = Despesa
    extra = 0
    fields = ('descricao', 'categoria', 'valor_total', 'data_vencimento', 'status')
    readonly_fields = ('data_cadastro',)

@admin.register(Despesa)
class DespesaAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'usuario', 'categoria', 'caminhao', 'valor_total', 'data_vencimento', 'status')
    list_filter = ('status', 'categoria', 'usuario')
    search_fields = ('descricao', 'observacoes', 'caminhao__placa_cavalo')
    readonly_fields = ('data_cadastro', 'data_atualizacao')
    actions = ['marcar_como_pago']

    def marcar_como_pago(self, request, queryset):
        updated = 0
        for d in queryset:
            d.status = 'PAGO'
            if not d.data_pagamento:
                d.data_pagamento = timezone.now().date()
            d.save()
            updated += 1
        self.message_user(request, f"{updated} despesas marcadas como pagas.")
    marcar_como_pago.short_description = "Marcar despesas selecionadas como pagas"

@admin.register(FuncionarioDespesa)
class FuncionarioDespesaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cargo', 'salario_mensal', 'ativo', 'data_admissao')
    actions = ['gerar_despesas_ano']

    def gerar_despesas_ano(self, request, queryset):
        created = 0
        for func in queryset:
            cat = CategoriaDespesa.objects.filter(usuario=func.usuario, nome='SALARIO').first()
            if not cat:
                continue
            func.gerar_despesas_salariais_ano(categoria_salario=cat)
            created += 12
        self.message_user(request, f"{created} despesas criadas (aprox).")
    gerar_despesas_ano.short_description = "Gerar despesas salariais anual (12 meses)"
