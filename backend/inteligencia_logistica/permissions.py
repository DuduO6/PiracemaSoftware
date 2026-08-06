from rest_framework.permissions import BasePermission

from .models import MembroEmpresa


class EmpresaAtivaPermission(BasePermission):
    message = "Informe uma empresa ativa à qual o usuário pertença no cabeçalho X-Empresa-ID."

    def has_permission(self, request, view):
        empresa_id = request.headers.get("X-Empresa-ID")
        membro = MembroEmpresa.objects.select_related("empresa").filter(
            empresa_id=empresa_id, usuario=request.user, ativo=True, empresa__ativo=True
        ).first()
        if not membro:
            return False
        request.empresa_logistica = membro.empresa
        request.membro_empresa = membro
        return request.method in ("GET", "HEAD", "OPTIONS") or membro.papel != MembroEmpresa.Papel.LEITURA
