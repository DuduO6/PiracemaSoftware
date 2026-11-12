from rest_framework.permissions import BasePermission

from inteligencia_logistica.models import MembroEmpresa


class MdfeEmpresaPermission(BasePermission):
    message = "Informe uma empresa ativa à qual o usuário pertença no cabeçalho X-Empresa-ID."

    def has_permission(self, request, view):
        empresa_id = request.headers.get("X-Empresa-ID")
        member = MembroEmpresa.objects.select_related("empresa").filter(
            empresa_id=empresa_id,
            usuario=request.user,
            ativo=True,
            empresa__ativo=True,
        ).first()
        if not member:
            return False
        request.empresa_logistica = member.empresa
        request.membro_empresa = member
        return True


class MdfeOperatorPermission(MdfeEmpresaPermission):
    message = "Seu perfil permite apenas consultar os MDF-e desta empresa."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.membro_empresa.papel != MembroEmpresa.Papel.LEITURA


class MdfeAdminPermission(MdfeEmpresaPermission):
    message = "Somente administradores da empresa podem alterar a configuração fiscal."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.membro_empresa.papel == MembroEmpresa.Papel.ADMIN
