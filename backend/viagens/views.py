from rest_framework import viewsets, permissions
from rest_framework import status
from .models import Viagem, Motorista, Vale
from .serializers import ViagemSerializer, AvaliadorViagemSerializer
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from datetime import datetime, timedelta
import csv
from io import BytesIO
from django.db.models import Q
from django.http import HttpResponse
from decimal import Decimal
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Image
from django.contrib.staticfiles import finders

# Importar os modelos de acerto
from acertos.models import Acerto, ItemAcerto, ValeAcerto, RegraAcerto
from fretes.exceptions import FretesError
from .services.cte_importer import parse_cte_xml
from .services.trip_profit_evaluator import avaliar_lucro_viagem


class ViagemViewSet(viewsets.ModelViewSet):
    serializer_class = ViagemSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Viagem.objects.filter(usuario=self.request.user)

    def _apply_trip_filters(self, queryset, params):
        motorista = params.get("motorista")
        cliente = (params.get("cliente") or "").strip()
        localidade = (params.get("localidade") or "").strip()
        pago = params.get("pago")
        inicio = params.get("inicio")
        fim = params.get("fim")
        teve_cte = params.get("teve_cte")

        if motorista:
            queryset = queryset.filter(motorista_id=motorista)

        if cliente:
            queryset = queryset.filter(cliente__icontains=cliente)

        if localidade:
            queryset = queryset.filter(Q(origem__icontains=localidade) | Q(destino__icontains=localidade))

        if pago == "nao_pago":
            queryset = queryset.filter(pago=False)
        elif pago == "pago":
            queryset = queryset.filter(pago=True)

        if inicio:
            queryset = queryset.filter(data__gte=inicio)

        if fim:
            queryset = queryset.filter(data__lte=fim)

        if teve_cte == "com_cte":
            queryset = queryset.filter(teve_cte=True)
        elif teve_cte == "sem_cte":
            queryset = queryset.filter(teve_cte=False)

        return queryset

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def importar_cte(self, request):
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            return Response({"detail": "Envie um arquivo XML de CT-e."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dados = parse_cte_xml(arquivo.read(), request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(dados, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def verificar_duplicidade(self, request):
        viagem_id = request.data.get("id")
        instance = None

        if viagem_id:
            try:
                instance = self.get_queryset().get(id=viagem_id)
            except Viagem.DoesNotExist:
                return Response({"detail": "Viagem não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance=instance, data=request.data, partial=bool(instance))
        serializer.is_valid(raise_exception=True)
        warning = serializer.build_duplicate_warning(serializer.validated_data)

        return Response(warning or {"duplicada": False}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def exportar_planilha(self, request):
        viagens = (
            self._apply_trip_filters(self.get_queryset(), request.query_params)
            .select_related("motorista")
            .order_by("-data", "-id")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="viagens_filtradas.csv"'
        response.write("\ufeff")

        writer = csv.writer(response, delimiter=";")
        writer.writerow([
            "Data",
            "Motorista",
            "Origem",
            "Destino",
            "Cliente",
            "Peso (TN)",
            "Valor/TN",
            "Valor Total",
            "Com CTE",
            "Numero CTE",
            "Pago",
        ])

        for viagem in viagens:
            writer.writerow([
                viagem.data.strftime("%d/%m/%Y"),
                viagem.motorista.nome if viagem.motorista_id else "",
                viagem.origem,
                viagem.destino,
                viagem.cliente,
                f"{viagem.peso:.2f}",
                f"{viagem.valor_tonelada:.2f}",
                f"{viagem.valor_total:.2f}",
                "Sim" if viagem.teve_cte else "Nao",
                viagem.numero_cte or "",
                "Sim" if viagem.pago else "Nao",
            ])

        return response

    @action(detail=False, methods=['post'])
    def avaliar_lucro(self, request):
        serializer = AvaliadorViagemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            viagem = self.get_queryset().select_related("motorista").get(id=serializer.validated_data["viagem_id"])
        except Viagem.DoesNotExist:
            return Response({"detail": "Viagem não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        try:
            resultado = avaliar_lucro_viagem(viagem=viagem, payload=serializer.validated_data)
        except FretesError as exc:
            response_payload = {"detail": exc.message, "code": exc.code}
            if exc.extra:
                response_payload.update(exc.extra)
            return Response(response_payload, status=exc.status_code)

        return Response(resultado, status=status.HTTP_200_OK)

    def _get_resumo_ultimo_acerto(self, motorista_id=None):
        acertos = Acerto.objects.filter(usuario=self.request.user).order_by('-data_geracao')
        if motorista_id:
            acertos = acertos.filter(motorista_id=motorista_id)

        ultimo_acerto = acertos.first()
        if not ultimo_acerto:
            return None

        ultimo_item = (
            ItemAcerto.objects.filter(acerto=ultimo_acerto)
            .order_by('-data', '-id')
            .first()
        )

        data_ultima_viagem = ultimo_item.data if ultimo_item else ultimo_acerto.data_fim
        inicio_sugerido = data_ultima_viagem + timedelta(days=1) if data_ultima_viagem else None

        return {
            "acerto_id": ultimo_acerto.id,
            "motorista_id": ultimo_acerto.motorista_id,
            "motorista_nome": ultimo_acerto.motorista.nome,
            "data_geracao": ultimo_acerto.data_geracao,
            "data_inicio": ultimo_acerto.data_inicio,
            "data_fim": ultimo_acerto.data_fim,
            "data_ultima_viagem_englobada": data_ultima_viagem,
            "inicio_sugerido": inicio_sugerido,
        }

    @action(detail=False, methods=['get'])
    def resumo_acerto(self, request):
        motorista_id = request.query_params.get('motorista_id')

        if motorista_id:
            try:
                motorista = Motorista.objects.get(id=motorista_id, usuario=request.user)
            except Motorista.DoesNotExist:
                return Response(
                    {"detail": "Motorista não encontrado."},
                    status=status.HTTP_404_NOT_FOUND
                )
            resumo = self._get_resumo_ultimo_acerto(motorista.id)
        else:
            resumo = self._get_resumo_ultimo_acerto()

        return Response(resumo or {})

    @action(detail=False, methods=['get'])
    def gerar_acerto(self, request):
        motorista_id = request.query_params.get('motorista_id')
        inicio = request.query_params.get('inicio')
        fim = request.query_params.get('fim')
        salvar = request.query_params.get('salvar', 'false').lower() == 'true'

        if not motorista_id or not inicio or not fim:
            return Response(
                {"detail": "Parâmetros obrigatórios: motorista_id, inicio e fim."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            inicio_date = datetime.strptime(inicio, "%Y-%m-%d").date()
            fim_date = datetime.strptime(fim, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"detail": "Formato de data inválido. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if inicio_date > fim_date:
            return Response(
                {"detail": "A data de início não pode ser maior que a data de fim."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            motorista = Motorista.objects.get(id=motorista_id, usuario=request.user)
        except Motorista.DoesNotExist:
            return Response(
                {"detail": "Motorista não encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        resumo_ultimo_acerto = self._get_resumo_ultimo_acerto(motorista.id)

        inicio_efetivo = inicio_date
        if resumo_ultimo_acerto and resumo_ultimo_acerto.get("inicio_sugerido"):
            inicio_efetivo = max(inicio_date, resumo_ultimo_acerto["inicio_sugerido"])

        if inicio_efetivo > fim_date:
            return Response(
                {
                    "detail": (
                        "Não há período válido para acerto após o último acerto desse motorista. "
                        "Ajuste a data de fim."
                    ),
                    "inicio_sugerido": resumo_ultimo_acerto.get("inicio_sugerido") if resumo_ultimo_acerto else None,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        viagens = self.get_queryset().filter(
            motorista_id=motorista_id,
            data__gte=inicio_efetivo,
            data__lte=fim_date
        ).order_by('data')

        vales = Vale.objects.filter(
            motorista_id=motorista_id,
            pago=False
        )

        total_valor = sum(v.valor_total for v in viagens)
        total_vales = sum(v.valor for v in vales)
        regra_acerto = (
            RegraAcerto.objects.filter(usuario=request.user, ativo=True)
            .order_by("-data_atualizacao", "-id")
            .first()
        )
        percentual_comissao = regra_acerto.percentual_comissao if regra_acerto else Decimal("13.00")
        desconto_fixo = regra_acerto.desconto_fixo if regra_acerto else Decimal("0.00")
        aplicar_vales = regra_acerto.aplicar_vales_pendentes if regra_acerto else True
        desconto_vales = total_vales if aplicar_vales else Decimal("0.00")
        comissao = total_valor * (percentual_comissao / Decimal("100"))
        total_viagens = viagens.count()
        valor_a_receber = comissao - desconto_vales - desconto_fixo

        # SALVAR HISTÓRICO DE ACERTO
        if salvar:
            acerto = Acerto.objects.create(
                usuario=request.user,
                motorista=motorista,
                data_inicio=inicio_efetivo,
                data_fim=fim_date,
                total_viagens=total_viagens,
                valor_total_viagens=total_valor,
                total_vales=total_vales,
                comissao=comissao,
                valor_a_receber=valor_a_receber,
                desconto_fixo=desconto_fixo,
                desconto_vales=desconto_vales,
                percentual_comissao=percentual_comissao,
                regra_aplicada=regra_acerto,
            )

            # Salvar itens (viagens)
            for v in viagens:
                ItemAcerto.objects.create(
                    acerto=acerto,
                    viagem=v,
                    data=v.data,
                    origem=v.origem,
                    destino=v.destino,
                    cliente=v.cliente,
                    peso=v.peso,
                    valor_tonelada=v.valor_tonelada,
                    valor_total=v.valor_total,
                    pago=v.pago
                )

            # Salvar vales
            for vale in vales:
                ValeAcerto.objects.create(
                    acerto=acerto,
                    vale=vale,
                    data=vale.data,
                    valor=vale.valor
                )

        # GERAR PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=40, 
            rightMargin=40, 
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        elementos = []

        logo_path = finders.find("viagens/logo.png")
        img_w = 140
        img_h = 70

        def draw_header(canvas_obj, doc_obj):
            if logo_path:
                page_w, page_h = A4
                x = page_w - doc_obj.rightMargin - img_w
                y = page_h - img_h - 10
                try:
                    canvas_obj.drawImage(
                        logo_path, 
                        x, y, 
                        width=img_w, 
                        height=img_h, 
                        preserveAspectRatio=True, 
                        mask='auto'
                    )
                except Exception as e:
                    pass
            
            canvas_obj.setFont("Helvetica", 9)
            page_num = canvas_obj.getPageNumber()
            text = f"Página {page_num}"
            canvas_obj.drawRightString(page_w - doc_obj.rightMargin, 20, text)

        titulo = Paragraph(
            f"<b>ACERTO DE FRETES</b><br/><b>Motorista:</b> {motorista.nome}",
            styles["Title"]
        )
        elementos.append(titulo)
        elementos.append(Spacer(1, 12))

        info = Paragraph(
            f"<b>Período:</b> {inicio_efetivo.strftime('%Y-%m-%d')} até {fim}<br/>"
            f"<b>Total de viagens:</b> {total_viagens}<br/>"
            f"<b>Comissão:</b> {percentual_comissao}%",
            styles["Heading3"]
        )
        elementos.append(info)
        elementos.append(Spacer(1, 20))

        tabela_dados = [
            ["DATA", "ORIGEM", "DESTINO", "CLIENTE", "PESO(TN)", "VALOR P/TN", "VALOR", "PAGO"]
        ]

        for v in viagens:
            tabela_dados.append([
                v.data.strftime("%d/%m/%Y"),
                v.origem or "",
                v.destino or "",
                v.cliente or "",
                f"{v.peso}",
                f"R$ {v.valor_tonelada}",
                f"R$ {v.valor_total}",
                "SIM" if v.pago else "NÃO"
            ])

        col_widths = [2.2*cm, 3*cm, 3*cm, 3.5*cm, 2*cm, 2.2*cm, 2.2*cm, 1.5*cm]
        
        tabela = Table(tabela_dados, colWidths=col_widths, repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.8, colors.black),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ]))

        elementos.append(Paragraph("<b>Viagens no período</b>", styles["Heading2"]))
        elementos.append(tabela)
        elementos.append(Spacer(1, 20))

        elementos.append(Paragraph("<b>Vales não pagos</b>", styles["Heading2"]))

        if vales.exists():
            tabela_vales = [["DATA", "VALOR"]]

            for vale in vales:
                tabela_vales.append([
                    vale.data.strftime("%d/%m/%Y"),
                    f"R$ {vale.valor}",
                ])

            tabela2 = Table(tabela_vales, colWidths=[4*cm, 4*cm], repeatRows=1)
            tabela2.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("GRID", (0,0), (-1,-1), 0.8, colors.black),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
            ]))

            elementos.append(tabela2)
        else:
            elementos.append(Paragraph("Nenhum vale pendente.", styles["Normal"]))

        elementos.append(Spacer(1, 20))

        resumo = Paragraph(
            f"<b>VALOR TOTAL DAS VIAGENS:</b> R$ {total_valor}<br/>"
            f"<b>TOTAL DE VALES:</b> R$ {desconto_vales}<br/>"
            f"<b>DESCONTO FIXO:</b> R$ {desconto_fixo}<br/>"
            f"<b>COMISSÃO ({percentual_comissao}%):</b> R$ {comissao}"
            f"<br/><b>VALOR A RECEBER:</b> R$ {valor_a_receber}",
            styles["Heading3"]
        )
        elementos.append(resumo)

        doc.build(elementos, onFirstPage=draw_header, onLaterPages=draw_header)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="acerto_fretes_{motorista.nome}_{inicio}_{fim}.pdf"'
        )
        return response
