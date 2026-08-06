from decimal import Decimal

from rest_framework import permissions, status, viewsets
from django.db import transaction
from django.utils.text import slugify
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (ConfiguracaoLogisticaEmpresa, DecisaoLogistica, Empresa, LocalLogistico,
                     IndicadorFrete, MembroEmpresa, ModeloLogisticoIA, OportunidadeFrete, ParceiroFrete,
                     PerfilEstrategia, PoloLogisticoNacional, ProdutoLogistico, ResultadoAprendizadoLogistico,
                     RotaEstrategica)
from .ml import features_oportunidade
from .permissions import EmpresaAtivaPermission
from .planner import planejar_reposicionamento
from .regioes import regioes_serializadas
from fretes.services.geocoding_service import GeocodingService
from fretes.services.routing_service import RoutingService
from fretes.services.toll_service import TollService
from .serializers import (CalculadoraFreteSerializer, ConfiguracaoSerializer, DecisaoSerializer,
                          IndicadorFreteSerializer, LocalLogisticoSerializer, ModeloIASerializer,
                          OportunidadeSerializer, ParceiroFreteSerializer,
                          PerfilEstrategiaSerializer, PlanejamentoReposicionamentoSerializer,
                          PoloLogisticoNacionalSerializer, ProdutoLogisticoSerializer, RecomendacaoSerializer,
                          RotaEstrategicaSerializer)
from .services import recomendar


class MinhasEmpresasView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        membros = MembroEmpresa.objects.select_related("empresa").filter(
            usuario=request.user, ativo=True, empresa__ativo=True
        ).order_by("empresa__nome")
        return Response([
            {"id": membro.empresa_id, "nome": membro.empresa.nome, "papel": membro.papel}
            for membro in membros
        ])

    @transaction.atomic
    def post(self, request):
        membro = MembroEmpresa.objects.select_related("empresa").filter(
            usuario=request.user, ativo=True, empresa__ativo=True
        ).first()
        if membro:
            return Response({"id": membro.empresa_id, "nome": membro.empresa.nome, "papel": membro.papel})
        nome_usuario = request.user.get_full_name().strip() or request.user.get_username()
        slug = f"{slugify(nome_usuario) or 'empresa'}-{request.user.id}"
        empresa, _ = Empresa.objects.get_or_create(
            slug=slug, defaults={"nome": f"Transportadora {nome_usuario}"[:160]}
        )
        membro, _ = MembroEmpresa.objects.get_or_create(
            empresa=empresa, usuario=request.user, defaults={"papel": MembroEmpresa.Papel.ADMIN, "ativo": True}
        )
        if not membro.ativo:
            membro.ativo = True
            membro.papel = MembroEmpresa.Papel.ADMIN
            membro.save(update_fields=("ativo", "papel"))
        ConfiguracaoLogisticaEmpresa.objects.get_or_create(empresa=empresa, nivel="GLOBAL")
        return Response({"id": empresa.id, "nome": empresa.nome, "papel": membro.papel}, status=status.HTTP_201_CREATED)


class RegioesLogisticasView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        return Response(regioes_serializadas())


class CalculadoraFreteView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        entrada = CalculadoraFreteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        try:
            geocoder = GeocodingService()
            origem = geocoder.geocode(dados["origem"], dados["estado_origem"], target="origem")
            destino = geocoder.geocode(dados["destino"], dados["estado_destino"], target="destino")
            payload_rota = {"tipo_veiculo": f"caminhao_{dados['eixos']}_eixos", "quantidade_eixos": dados["eixos"]}
            rota = RoutingService().calculate_route(origem, destino, payload_rota)
            pedagios_calculados = TollService().estimate_tolls(origem, destino, rota, payload_rota)
        except Exception as exc:
            return Response({"detail": f"Não foi possível calcular a rota: {exc}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        pedagios_provedor = pedagios_calculados["total"] if pedagios_calculados.get("disponivel") else None
        pedagios_informado = dados.get("valor_pedagios_informado")
        pedagios = pedagios_informado if pedagios_informado is not None else pedagios_provedor
        distancia = Decimal(str(rota["distancia_km"]))
        frete = dados["valor_frete"]
        liquido_pedagios = frete - Decimal(str(pedagios or 0))
        return Response({
            "origem": origem, "destino": destino, "distancia_km": float(distancia),
            "duracao": rota.get("duracao_formatada"), "rodovias_referencia": rota.get("rodovias_referencia", []),
            "valor_frete": float(frete), "valor_pedagios": float(pedagios) if pedagios is not None else None,
            "pedagios_origem": "INFORMADO" if pedagios_informado is not None else ("PROVEDOR" if pedagios_provedor is not None else "INDISPONIVEL"),
            "valor_liquido_apos_pedagios": float(round(liquido_pedagios, 2)),
            "valor_km_bruto": float(round(frete / distancia, 2)) if distancia else None,
            "valor_km_apos_pedagios": float(round(liquido_pedagios / distancia, 2)) if distancia else None,
            "eixos": dados["eixos"], "provedor_rota": rota.get("provedor"),
            "pedagios": pedagios_calculados.get("itens", []),
            "provedor_pedagios": pedagios_calculados.get("provedor"),
            "aviso_pedagios": None if pedagios is not None else pedagios_calculados.get("mensagem", "Informe o total para completar a simulação."),
        })


class PlanejamentoReposicionamentoView(APIView):
    permission_classes = (permissions.IsAuthenticated, EmpresaAtivaPermission)

    def post(self, request):
        entrada = PlanejamentoReposicionamentoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            resultado = planejar_reposicionamento(
                usuario=request.user, empresa=request.empresa_logistica, **entrada.validated_data
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"detail": f"Não foi possível consultar mapas e rotas neste momento: {exc}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(resultado)


class PoloNacionalViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PoloLogisticoNacionalSerializer
    queryset = PoloLogisticoNacional.objects.prefetch_related("categorias").filter(ativo=True)

    def get_queryset(self):
        queryset = super().get_queryset()
        categoria = self.request.query_params.get("categoria")
        estado = self.request.query_params.get("estado")
        busca = self.request.query_params.get("busca")
        if categoria:
            queryset = queryset.filter(categorias__codigo=categoria)
        if estado:
            queryset = queryset.filter(estado__iexact=estado)
        if busca:
            queryset = queryset.filter(cidade__icontains=busca)
        return queryset.distinct().order_by("-nivel_importancia", "cidade")


class ProdutoLogisticoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ProdutoLogisticoSerializer
    queryset = ProdutoLogistico.objects.prefetch_related("veiculos_permitidos").filter(ativo=True).order_by("produto")


class IndicadorFreteViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = IndicadorFreteSerializer
    queryset = IndicadorFrete.objects.select_related("produto").order_by("produto__produto", "faixa_distancia")


class TenantViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.IsAuthenticated, EmpresaAtivaPermission)

    def get_queryset(self):
        return self.queryset.filter(empresa=self.request.empresa_logistica)

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.empresa_logistica)


class LocalLogisticoViewSet(TenantViewSet):
    queryset = LocalLogistico.objects.all()
    serializer_class = LocalLogisticoSerializer


class ParceiroFreteViewSet(TenantViewSet):
    queryset = ParceiroFrete.objects.all()
    serializer_class = ParceiroFreteSerializer


class RotaEstrategicaViewSet(TenantViewSet):
    queryset = RotaEstrategica.objects.all()
    serializer_class = RotaEstrategicaSerializer


class PerfilEstrategiaViewSet(TenantViewSet):
    queryset = PerfilEstrategia.objects.all()
    serializer_class = PerfilEstrategiaSerializer


class ConfiguracaoViewSet(TenantViewSet):
    queryset = ConfiguracaoLogisticaEmpresa.objects.all()
    serializer_class = ConfiguracaoSerializer


class ModeloIAViewSet(TenantViewSet):
    queryset = ModeloLogisticoIA.objects.all()
    serializer_class = ModeloIASerializer


class DecisaoViewSet(TenantViewSet):
    queryset = DecisaoLogistica.objects.all()
    serializer_class = DecisaoSerializer

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.empresa_logistica, criado_por=self.request.user)

    @action(detail=True, methods=("post",))
    def feedback(self, request, pk=None):
        decisao = self.get_object()
        decisao.avaliacao = request.data.get("avaliacao", "")
        decisao.motivo_feedback = request.data.get("motivo", "")
        decisao.resultado_real = request.data.get("resultado_real", {})
        decisao.save(update_fields=("avaliacao", "motivo_feedback", "resultado_real"))
        valores = request.data.get("resultado_real") or {}
        resultado, _ = ResultadoAprendizadoLogistico.objects.get_or_create(
            decisao=decisao, defaults={"empresa": decisao.empresa, "oportunidade": decisao.oportunidade_recomendada,
                                      "features": features_oportunidade(decisao.oportunidade_recomendada)}
        )
        campos = {
            "aceitou_sugestao": request.data.get("aceitou_sugestao"),
            "lucro_real": valores.get("lucro_liquido"), "receita_real": valores.get("receita"),
            "custos_reais": valores.get("custos_totais"), "km_vazio_real": valores.get("km_vazio"),
            "tempo_espera_real_horas": valores.get("tempo_espera_horas"),
            "retorno_vazio_real": valores.get("retorno_vazio"),
        }
        for campo, valor in campos.items():
            if valor is not None:
                setattr(resultado, campo, valor)
        resultado.save()
        return Response(self.get_serializer(decisao).data)


class OportunidadeViewSet(TenantViewSet):
    queryset = OportunidadeFrete.objects.select_related("parceiro")
    serializer_class = OportunidadeSerializer

    @action(detail=False, methods=("post",))
    def recomendar(self, request):
        entrada = RecomendacaoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        dados = entrada.validated_data
        oportunidades = list(self.get_queryset().filter(id__in=dados.pop("oportunidade_ids")))
        perfil_id = dados.pop("perfil_id", None)
        perfil = None
        if perfil_id:
            perfil = PerfilEstrategia.objects.filter(empresa=request.empresa_logistica, id=perfil_id, ativo=True).first()
            if not perfil:
                return Response({"detail": "Perfil não encontrado na empresa ativa."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resultado = recomendar(request.empresa_logistica, oportunidades, perfil, dados)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        recomendada = self.get_queryset().get(id=resultado["recomendada"]["oportunidade_id"])
        decisao = DecisaoLogistica.objects.create(
            empresa=request.empresa_logistica, perfil=perfil, oportunidade_recomendada=recomendada,
            alternativas=resultado["alternativas"], explicacao=resultado["explicacao"],
            avisos=resultado["avisos"], modo=resultado["modo"], criado_por=request.user,
        )
        ResultadoAprendizadoLogistico.objects.create(
            empresa=request.empresa_logistica, decisao=decisao, oportunidade=recomendada,
            features=features_oportunidade(recomendada), lucro_previsto=resultado["recomendada"]["lucro_esperado_ciclo"],
        )
        resultado["recommendation_id"] = decisao.id
        return Response(resultado, status=status.HTTP_201_CREATED)
