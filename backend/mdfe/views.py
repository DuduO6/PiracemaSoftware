from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.utils.text import slugify
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from inteligencia_logistica.models import Empresa, MembroEmpresa

from .models import ConfiguracaoFiscal, ConsultaManifestos, Manifesto, OperacaoEncerramento
from .permissions import MdfeAdminPermission, MdfeEmpresaPermission, MdfeOperatorPermission
from .serializers import (
    ConfiguracaoFiscalSerializer,
    ConsultaSerializer,
    EncerramentoInputSerializer,
    ManifestoSerializer,
    OperacaoEncerramentoSerializer,
)
from .services.certificate_service import (
    certificate_metadata,
    decrypt_secret,
    encrypt_secret,
    load_configuration_material,
    load_pkcs12,
)
from .services.consulta_service import ConsultaMdfeService
from .services.encerramento_service import EncerramentoMdfeService
from .services.exceptions import MdfeError
from .services.validators import normalize_cnpj, normalize_uf
from .services.xml_import_service import MAX_XML_BYTES, MdfeXmlImportService


def error_response(exc):
    payload = {"detail": exc.message, "code": exc.code}
    payload.update(exc.details)
    return Response(payload, status=exc.status_code)


def fiscal_configuration(request):
    try:
        return ConfiguracaoFiscal.objects.get(empresa=request.empresa_logistica)
    except ConfiguracaoFiscal.DoesNotExist as exc:
        raise MdfeError(
            "A configuração fiscal da transportadora ainda não foi cadastrada.",
            code="mdfe_not_configured",
            status_code=409,
        ) from exc


class MdfeCompaniesView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        memberships = MembroEmpresa.objects.select_related("empresa").filter(
            usuario=request.user, ativo=True, empresa__ativo=True
        ).order_by("empresa__nome")
        return Response([
            {"id": membership.empresa_id, "nome": membership.empresa.nome, "papel": membership.papel}
            for membership in memberships
        ])

    @transaction.atomic
    def post(self, request):
        membership = MembroEmpresa.objects.select_related("empresa").filter(
            usuario=request.user, ativo=True, empresa__ativo=True
        ).first()
        if membership:
            return Response({
                "id": membership.empresa_id,
                "nome": membership.empresa.nome,
                "papel": membership.papel,
            })
        display_name = request.user.get_full_name().strip() or request.user.get_username()
        slug = f"{slugify(display_name) or 'empresa'}-{request.user.id}"
        company, _ = Empresa.objects.get_or_create(
            slug=slug, defaults={"nome": f"Transportadora {display_name}"[:160]}
        )
        membership, _ = MembroEmpresa.objects.get_or_create(
            empresa=company,
            usuario=request.user,
            defaults={"papel": MembroEmpresa.Papel.ADMIN, "ativo": True},
        )
        if not membership.ativo or membership.papel != MembroEmpresa.Papel.ADMIN:
            membership.ativo = True
            membership.papel = MembroEmpresa.Papel.ADMIN
            membership.save(update_fields=("ativo", "papel"))
        return Response(
            {"id": company.id, "nome": company.nome, "papel": membership.papel},
            status=status.HTTP_201_CREATED,
        )


class MdfePagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


class ManifestListView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeEmpresaPermission)

    def get(self, request):
        queryset = Manifesto.objects.filter(empresa=request.empresa_logistica).prefetch_related(
            "condutores__motorista"
        ).order_by("-ultima_consulta_em", "-id")
        search = (request.query_params.get("search") or "").strip()
        situation = (request.query_params.get("situacao") or "").strip().upper()
        if search:
            queryset = queryset.filter(
                Q(chave__icontains=search)
                | Q(numero__icontains=search)
                | Q(condutores__nome_xml__icontains=search)
                | Q(condutores__motorista__nome__icontains=search)
            ).distinct()
        if situation:
            queryset = queryset.filter(situacao=situation)
        else:
            queryset = queryset.exclude(situacao=Manifesto.Situacao.ENCERRADO)

        paginator = MdfePagination()
        page = paginator.paginate_queryset(queryset, request)
        latest = ConsultaManifestos.objects.filter(empresa=request.empresa_logistica).first()
        last_success = ConsultaManifestos.objects.filter(
            empresa=request.empresa_logistica, estado=ConsultaManifestos.Estado.SUCESSO
        ).first()
        counts = Manifesto.objects.filter(empresa=request.empresa_logistica).aggregate(
            abertos=Count("id", filter=Q(situacao=Manifesto.Situacao.ABERTO)),
            encerrados=Count("id", filter=Q(situacao=Manifesto.Situacao.ENCERRADO)),
            pendentes=Count("id", filter=Q(situacao__in=(Manifesto.Situacao.A_CONFIRMAR, Manifesto.Situacao.DESCONHECIDO))),
        )
        return paginator.get_paginated_response({
            "items": ManifestoSerializer(page, many=True).data,
            "resumo": counts,
            "consulta": {
                "desatualizado": bool(latest and latest.estado != ConsultaManifestos.Estado.SUCESSO),
                "ultima_tentativa": ConsultaSerializer(latest).data if latest else None,
                "ultima_consulta_bem_sucedida": ConsultaSerializer(last_success).data if last_success else None,
            },
        })


class ManifestHistoryView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeEmpresaPermission)

    def get(self, request):
        queryset = Manifesto.objects.filter(
            empresa=request.empresa_logistica, situacao=Manifesto.Situacao.ENCERRADO
        ).prefetch_related("condutores__motorista").order_by("-encerrado_em", "-id")
        search = (request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(chave__icontains=search)
                | Q(numero__icontains=search)
                | Q(condutores__nome_xml__icontains=search)
                | Q(condutores__motorista__nome__icontains=search)
            ).distinct()
        paginator = MdfePagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(ManifestoSerializer(page, many=True).data)


class ManifestDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeEmpresaPermission)

    def get(self, request, chave):
        try:
            manifest = Manifesto.objects.prefetch_related("condutores__motorista").get(
                empresa=request.empresa_logistica, chave=chave
            )
        except Manifesto.DoesNotExist:
            return Response({"detail": "MDF-e não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ManifestoSerializer(manifest).data)


class ManifestXmlImportView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeOperatorPermission)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        files = request.FILES.getlist("arquivos") or request.FILES.getlist("arquivo")
        if not files:
            return Response({"detail": "Selecione ao menos um arquivo XML."}, status=status.HTTP_400_BAD_REQUEST)
        if len(files) > 20:
            return Response({"detail": "Importe no máximo 20 arquivos por vez."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            service = MdfeXmlImportService(fiscal_configuration(request))
        except MdfeError as exc:
            return error_response(exc)

        imported = []
        errors = []
        for uploaded in files:
            safe_name = Path(uploaded.name).name[:180]
            if Path(safe_name).suffix.lower() != ".xml":
                errors.append({"arquivo": safe_name, "detail": "O arquivo deve ter extensão .xml.", "code": "invalid_file_type"})
                continue
            if uploaded.size > MAX_XML_BYTES:
                errors.append({"arquivo": safe_name, "detail": "O XML deve ter no máximo 5 MB.", "code": "file_too_large"})
                continue
            try:
                result = service.import_document(uploaded.read())
                result["arquivo"] = safe_name
                imported.append(result)
            except MdfeError as exc:
                errors.append({"arquivo": safe_name, "detail": exc.message, "code": exc.code})
            except Exception:
                errors.append({"arquivo": safe_name, "detail": "Falha inesperada ao importar o XML.", "code": "xml_import_error"})

        response_status = status.HTTP_200_OK
        if errors and imported:
            response_status = status.HTTP_207_MULTI_STATUS
        elif errors and not imported:
            response_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response(
            {"importados": imported, "erros": errors, "total_importados": len(imported), "total_erros": len(errors)},
            status=response_status,
        )


class ManifestRefreshView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeEmpresaPermission)

    def post(self, request):
        try:
            configuration = fiscal_configuration(request)
            audit = ConsultaMdfeService(configuration).refresh_non_closed(request.user)
            return Response(ConsultaSerializer(audit).data)
        except MdfeError as exc:
            payload = error_response(exc)
            last_success = ConsultaManifestos.objects.filter(
                empresa=request.empresa_logistica, estado=ConsultaManifestos.Estado.SUCESSO
            ).first()
            payload.data["desatualizado"] = True
            payload.data["ultima_consulta_bem_sucedida"] = ConsultaSerializer(last_success).data if last_success else None
            return payload


class ManifestCloseView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeOperatorPermission)

    def post(self, request, chave):
        serializer = EncerramentoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            configuration = fiscal_configuration(request)
            manifest = Manifesto.objects.get(empresa=request.empresa_logistica, chave=chave)
            operation = EncerramentoMdfeService(configuration).close(
                manifest,
                user=request.user,
                uf=serializer.validated_data["uf"],
                municipality_code=serializer.validated_data["municipio_codigo"],
                closing_date=serializer.validated_data["data_encerramento"],
                idempotency_key=request.headers.get("Idempotency-Key", "")[:200],
            )
        except Manifesto.DoesNotExist:
            return Response({"detail": "MDF-e não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except MdfeError as exc:
            return error_response(exc)
        except Exception:
            return Response(
                {"detail": "Falha ao persistir a operação de encerramento.", "code": "persistence_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_status = status.HTTP_200_OK
        if operation.estado in (OperacaoEncerramento.Estado.PROCESSANDO, OperacaoEncerramento.Estado.A_CONFIRMAR):
            response_status = status.HTTP_202_ACCEPTED
        elif operation.estado in (OperacaoEncerramento.Estado.REJEITADO, OperacaoEncerramento.Estado.ERRO):
            response_status = status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response(OperacaoEncerramentoSerializer(operation).data, status=response_status)


class OperationDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeEmpresaPermission)

    def get_object(self, request, operation_id):
        return OperacaoEncerramento.objects.select_related("manifesto").filter(
            pk=operation_id, manifesto__empresa=request.empresa_logistica
        ).first()

    def get(self, request, operation_id):
        operation = self.get_object(request, operation_id)
        if not operation:
            return Response({"detail": "Operação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(OperacaoEncerramentoSerializer(operation).data)


class OperationConfirmView(OperationDetailView):
    permission_classes = (permissions.IsAuthenticated, MdfeOperatorPermission)

    def post(self, request, operation_id):
        operation = self.get_object(request, operation_id)
        if not operation:
            return Response({"detail": "Operação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        try:
            configuration = fiscal_configuration(request)
            operation = EncerramentoMdfeService(configuration).confirm_pending(operation)
        except MdfeError as exc:
            return error_response(exc)
        response_status = status.HTTP_202_ACCEPTED if operation.estado == OperacaoEncerramento.Estado.A_CONFIRMAR else status.HTTP_200_OK
        return Response(OperacaoEncerramentoSerializer(operation).data, status=response_status)


class FiscalConfigurationView(APIView):
    permission_classes = (permissions.IsAuthenticated, MdfeAdminPermission)
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get(self, request):
        configuration = ConfiguracaoFiscal.objects.filter(empresa=request.empresa_logistica).first()
        if not configuration:
            return Response({"configurado": False})
        data = ConfiguracaoFiscalSerializer(configuration).data
        data["configurado"] = True
        data["producao_disponivel_no_servidor"] = settings.MDFE_ENABLE_PRODUCTION
        return Response(data)

    def put(self, request):
        existing = ConfiguracaoFiscal.objects.filter(empresa=request.empresa_logistica).first()
        data = request.data
        try:
            cnpj = normalize_cnpj(data.get("cnpj", existing.cnpj if existing else ""))
            uf = normalize_uf(data.get("uf", existing.uf if existing else ""))
        except MdfeError as exc:
            return error_response(exc)
        razao_social = str(data.get("razao_social", existing.razao_social if existing else "")).strip()
        if not razao_social:
            return Response({"razao_social": ["Informe a razão social."]}, status=status.HTTP_400_BAD_REQUEST)
        ambiente = str(data.get("ambiente", existing.ambiente if existing else "HOMOLOGACAO")).upper()
        if ambiente not in ConfiguracaoFiscal.Ambiente.values:
            return Response({"ambiente": ["Ambiente fiscal inválido."]}, status=status.HTTP_400_BAD_REQUEST)

        confirm_production = str(data.get("confirmar_producao", "")).lower() in ("1", "true", "sim", "yes")
        already_enabled = bool(existing and existing.ambiente == "PRODUCAO" and existing.producao_liberada)
        if ambiente == "PRODUCAO" and not (settings.MDFE_ENABLE_PRODUCTION and (confirm_production or already_enabled)):
            return Response(
                {"detail": "Produção exige MDFE_ENABLE_PRODUCTION=True e confirmação administrativa explícita.", "code": "production_not_enabled"},
                status=status.HTTP_409_CONFLICT,
            )

        uploaded = request.FILES.get("certificado")
        supplied_password = data.get("senha_certificado")
        if uploaded:
            if Path(uploaded.name).suffix.lower() not in (".pfx", ".p12"):
                return Response({"certificado": ["Envie um certificado .pfx ou .p12."]}, status=400)
            if uploaded.size > 10 * 1024 * 1024:
                return Response({"certificado": ["O certificado deve ter no máximo 10 MB."]}, status=400)
            if supplied_password is None:
                return Response({"senha_certificado": ["Informe a senha do certificado."]}, status=400)
            certificate_bytes = uploaded.read()
            try:
                material = load_pkcs12(certificate_bytes, supplied_password, expected_cnpj=cnpj)
            except MdfeError as exc:
                return error_response(exc)
            metadata = certificate_metadata(material)
            try:
                encrypted_certificate = encrypt_secret(certificate_bytes)
                encrypted_password = encrypt_secret(str(supplied_password).encode("utf-8"))
            except MdfeError as exc:
                return error_response(exc)
            certificate_name = Path(uploaded.name).name[:180]
        elif existing:
            if supplied_password not in (None, ""):
                return Response(
                    {"senha_certificado": ["Envie também o novo arquivo do certificado para alterar a senha."]}, status=400
                )
            try:
                material = load_pkcs12(
                    decrypt_secret(existing.certificado_criptografado),
                    decrypt_secret(existing.senha_criptografada).decode("utf-8"),
                    expected_cnpj=cnpj,
                )
            except MdfeError as exc:
                return error_response(exc)
            metadata = certificate_metadata(material)
            encrypted_certificate = existing.certificado_criptografado
            encrypted_password = existing.senha_criptografada
            certificate_name = existing.certificado_nome
        else:
            return Response({"certificado": ["Envie o certificado A1 da transportadora."]}, status=400)

        configuration, _ = ConfiguracaoFiscal.objects.update_or_create(
            empresa=request.empresa_logistica,
            defaults={
                "razao_social": razao_social,
                "cnpj": cnpj,
                "uf": uf,
                "ambiente": ambiente,
                "producao_liberada": ambiente == "PRODUCAO" and settings.MDFE_ENABLE_PRODUCTION,
                "certificado_criptografado": encrypted_certificate,
                "senha_criptografada": encrypted_password,
                "certificado_nome": certificate_name,
                "certificado_fingerprint": metadata["fingerprint"],
                "certificado_cnpj": metadata["cnpj"],
                "certificado_valido_de": metadata["valid_from"],
                "certificado_valido_ate": metadata["valid_until"],
                "atualizado_por": request.user,
            },
        )
        response = ConfiguracaoFiscalSerializer(configuration).data
        response["configurado"] = True
        return Response(response)
