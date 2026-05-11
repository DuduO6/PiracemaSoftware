from rest_framework import viewsets, permissions
from rest_framework import status
from .models import Viagem, Motorista, Vale
from .serializers import ViagemSerializer, AvaliadorViagemSerializer
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from datetime import datetime, timedelta
import csv
import json
from io import BytesIO
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse
from decimal import Decimal, ROUND_HALF_UP
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
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


CASAS_DECIMAIS = Decimal("0.01")
PERCENTUAL_DESCONTO_CTE = Decimal("10")
FATOR_DESCONTO_CTE = PERCENTUAL_DESCONTO_CTE / Decimal("100")


def arredondar_moeda(valor):
    return valor.quantize(CASAS_DECIMAIS, rounding=ROUND_HALF_UP)


def get_bool_param(params, nome, default=False):
    valor = params.get(nome)
    if valor is None:
        return default
    return str(valor).lower() in ("1", "true", "sim", "yes")


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
            "Valor Bruto",
            "Desconto CTE",
            "Valor Liquido",
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
                f"{viagem.calcular_valor_bruto():.2f}",
                f"{arredondar_moeda(viagem.peso * viagem.valor_tonelada * FATOR_DESCONTO_CTE) if viagem.teve_cte else Decimal('0.00'):.2f}",
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
        descontar_vales = get_bool_param(request.query_params, "descontar_vales")
        vales_payload_raw = request.query_params.get("vales", "[]")

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

        try:
            vales_payload = json.loads(vales_payload_raw) if vales_payload_raw else []
        except json.JSONDecodeError:
            return Response(
                {"detail": "Lista de vales inválida."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(vales_payload, list):
            return Response(
                {"detail": "Lista de vales inválida."},
                status=status.HTTP_400_BAD_REQUEST
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

        viagens = list(self.get_queryset().filter(
            motorista_id=motorista_id,
            data__gte=inicio_efetivo,
            data__lte=fim_date
        ).order_by('data'))

        vales = []
        vales_selecionados = []
        if descontar_vales:
            for vale_item in vales_payload:
                try:
                    vale_id = int(vale_item.get("id"))
                    valor_desconto = arredondar_moeda(Decimal(str(vale_item.get("valor_desconto", "0"))))
                except (TypeError, ValueError, ArithmeticError):
                    return Response(
                        {"detail": "Informe valores válidos para os vales selecionados."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if valor_desconto <= 0:
                    return Response(
                        {"detail": "O desconto de vale deve ser maior que zero."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                try:
                    vale = Vale.objects.get(id=vale_id, motorista=motorista, pago=False)
                except Vale.DoesNotExist:
                    return Response(
                        {"detail": "Vale selecionado não encontrado ou já pago."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                saldo_atual = arredondar_moeda(vale.valor)
                if valor_desconto > saldo_atual:
                    return Response(
                        {"detail": f"O desconto do vale de {vale.data} não pode ser maior que R$ {saldo_atual}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                restante = arredondar_moeda(saldo_atual - valor_desconto)
                vales_selecionados.append({
                    "vale": vale,
                    "valor_original": saldo_atual,
                    "valor_desconto": valor_desconto,
                    "valor_restante": restante,
                    "quitado": restante == Decimal("0.00"),
                })
                vales.append(vale)

        total_valor = arredondar_moeda(sum((v.valor_total for v in viagens), Decimal("0.00")))
        viagens_com_cte = [v for v in viagens if v.teve_cte]
        viagens_sem_cte = [v for v in viagens if not v.teve_cte]
        total_viagens_com_cte = len(viagens_com_cte)
        valor_total_viagens_com_cte = arredondar_moeda(sum((v.valor_total for v in viagens_com_cte), Decimal("0.00")))
        valor_bruto_viagens_com_cte = arredondar_moeda(
            sum((v.calcular_valor_bruto() for v in viagens_com_cte), Decimal("0.00"))
        )
        total_viagens_sem_cte = len(viagens_sem_cte)
        valor_total_viagens_sem_cte = arredondar_moeda(sum((v.valor_total for v in viagens_sem_cte), Decimal("0.00")))
        desconto_cte_por_viagem = {
            v.id: arredondar_moeda((v.peso * v.valor_tonelada) * FATOR_DESCONTO_CTE) if v.teve_cte else Decimal("0.00")
            for v in viagens
        }
        desconto_cte = arredondar_moeda(sum(desconto_cte_por_viagem.values(), Decimal("0.00")))
        total_vales = arredondar_moeda(sum((item["valor_original"] for item in vales_selecionados), Decimal("0.00")))
        regra_acerto = (
            RegraAcerto.objects.filter(usuario=request.user, ativo=True)
            .order_by("-data_atualizacao", "-id")
            .first()
        )
        percentual_comissao = regra_acerto.percentual_comissao if regra_acerto else Decimal("13.00")
        desconto_fixo = regra_acerto.desconto_fixo if regra_acerto else Decimal("0.00")
        desconto_fixo = arredondar_moeda(desconto_fixo)
        desconto_vales = arredondar_moeda(sum((item["valor_desconto"] for item in vales_selecionados), Decimal("0.00")))
        comissao = arredondar_moeda(total_valor * (percentual_comissao / Decimal("100")))
        total_viagens = len(viagens)
        valor_a_receber = arredondar_moeda(comissao - desconto_vales - desconto_fixo)

        # SALVAR HISTÓRICO DE ACERTO
        if salvar:
            with transaction.atomic():
                acerto = Acerto.objects.create(
                    usuario=request.user,
                    motorista=motorista,
                    data_inicio=inicio_efetivo,
                    data_fim=fim_date,
                    total_viagens=total_viagens,
                    valor_total_viagens=total_valor,
                    total_viagens_com_cte=total_viagens_com_cte,
                    valor_total_viagens_com_cte=valor_total_viagens_com_cte,
                    total_viagens_sem_cte=total_viagens_sem_cte,
                    valor_total_viagens_sem_cte=valor_total_viagens_sem_cte,
                    desconto_cte=desconto_cte,
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
                        teve_cte=v.teve_cte,
                        valor_desconto_cte=desconto_cte_por_viagem[v.id],
                        pago=v.pago
                    )

                # Salvar e aplicar descontos de vales selecionados
                for item in vales_selecionados:
                    from motoristas.models import DescontoVale

                    vale = item["vale"]
                    ValeAcerto.objects.create(
                        acerto=acerto,
                        vale=vale,
                        data=vale.data,
                        valor_original=item["valor_original"],
                        valor=item["valor_desconto"],
                        valor_restante=item["valor_restante"],
                        quitado=item["quitado"],
                    )
                    vale.valor = item["valor_restante"]
                    vale.valor_descontado = arredondar_moeda((vale.valor_descontado or Decimal("0.00")) + item["valor_desconto"])
                    vale.pago = item["quitado"]
                    vale.save(update_fields=["valor", "valor_descontado", "pago"])
                    DescontoVale.objects.create(
                        vale=vale,
                        acerto=acerto,
                        valor=item["valor_desconto"],
                        saldo_antes=item["valor_original"],
                        saldo_depois=item["valor_restante"],
                    )

        # GERAR PDF
        buffer = BytesIO()
        page_size = landscape(A4)
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=page_size,
            leftMargin=40, 
            rightMargin=40, 
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        table_cell_style = ParagraphStyle(
            "TabelaAcertoCelula",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=8,
            alignment=1,
            wordWrap="CJK",
        )
        table_header_style = ParagraphStyle(
            "TabelaAcertoCabecalho",
            parent=table_cell_style,
            fontName="Helvetica-Bold",
        )
        elementos = []

        logo_path = finders.find("viagens/logo.png")
        img_w = 140
        img_h = 70

        def draw_header(canvas_obj, doc_obj):
            page_w, page_h = page_size
            if logo_path:
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
            f"<b>Viagens com CT-e:</b> {total_viagens_com_cte} - bruto R$ {valor_bruto_viagens_com_cte} | líquido R$ {valor_total_viagens_com_cte}<br/>"
            f"<b>Viagens sem CT-e:</b> {total_viagens_sem_cte} - R$ {valor_total_viagens_sem_cte}<br/>"
            f"<b>Desconto CT-e ({PERCENTUAL_DESCONTO_CTE}%):</b> R$ {desconto_cte}<br/>"
            f"<b>Comissão:</b> {percentual_comissao}%",
            styles["Heading3"]
        )
        elementos.append(info)
        elementos.append(Spacer(1, 20))

        tabela_dados = [[
            Paragraph("DATA", table_header_style),
            Paragraph("ORIGEM", table_header_style),
            Paragraph("DESTINO", table_header_style),
            Paragraph("CLIENTE", table_header_style),
            Paragraph("PESO(TN)", table_header_style),
            Paragraph("VALOR P/TN", table_header_style),
            Paragraph("VALOR BRUTO", table_header_style),
            Paragraph("DESC. CT-E", table_header_style),
            Paragraph("VALOR LIQ.", table_header_style),
            Paragraph("CT-E", table_header_style),
            Paragraph("PAGO", table_header_style),
        ]]

        for v in viagens:
            tabela_dados.append([
                Paragraph(v.data.strftime("%d/%m/%Y"), table_cell_style),
                Paragraph(v.origem or "", table_cell_style),
                Paragraph(v.destino or "", table_cell_style),
                Paragraph(v.cliente or "", table_cell_style),
                Paragraph(f"{v.peso}", table_cell_style),
                Paragraph(f"R$ {v.valor_tonelada}", table_cell_style),
                Paragraph(f"R$ {v.calcular_valor_bruto()}", table_cell_style),
                Paragraph(f"R$ {desconto_cte_por_viagem[v.id]}", table_cell_style),
                Paragraph(f"R$ {v.valor_total}", table_cell_style),
                Paragraph("SIM" if v.teve_cte else "NÃO", table_cell_style),
                Paragraph("SIM" if v.pago else "NÃO", table_cell_style),
            ])

        col_widths = [1.9*cm, 3.8*cm, 3.8*cm, 4.1*cm, 1.6*cm, 2*cm, 2*cm, 2*cm, 2*cm, 1.3*cm, 1.3*cm]
        
        tabela = Table(tabela_dados, colWidths=col_widths, repeatRows=1)
        tabela.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("GRID", (0,0), (-1,-1), 0.8, colors.black),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("LEFTPADDING", (0,0), (-1,-1), 3),
            ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ]))

        elementos.append(Paragraph("<b>Viagens no período</b>", styles["Heading2"]))
        elementos.append(tabela)
        elementos.append(Spacer(1, 20))

        elementos.append(Paragraph("<b>Vales selecionados para desconto</b>", styles["Heading2"]))

        tabela_vales = [["DATA", "SALDO ANTES", "DESCONTO", "SALDO APÓS", "SITUAÇÃO"]]
        if vales_selecionados:
            for item in vales_selecionados:
                vale = item["vale"]
                tabela_vales.append([
                    vale.data.strftime("%d/%m/%Y"),
                    f"R$ {item['valor_original']}",
                    f"R$ {item['valor_desconto']}",
                    f"R$ {item['valor_restante']}",
                    "QUITADO" if item["quitado"] else "PARCIAL",
                ])
        else:
            tabela_vales.append(["-", "-", "R$ 0.00", "-", "NENHUM VALE DESCONTADO"])

        tabela2 = Table(tabela_vales, colWidths=[3.5*cm, 4*cm, 4*cm, 4*cm, 5.5*cm], repeatRows=1)
        tabela2.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.8, colors.black),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.95, 0.95, 0.95)]),
        ]))
        elementos.append(tabela2)

        elementos.append(PageBreak())

        elementos.append(Paragraph("<b>Resumo do acerto</b>", styles["Heading2"]))
        resumo_dados = [
            ["DESCRIÇÃO", "QUANTIDADE", "VALOR"],
            ["Valor total líquido das viagens", str(total_viagens), f"R$ {total_valor}"],
            ["Viagens com CT-e - valor bruto", str(total_viagens_com_cte), f"R$ {valor_bruto_viagens_com_cte}"],
            [f"Desconto CT-e ({PERCENTUAL_DESCONTO_CTE}%)", "-", f"- R$ {desconto_cte}"],
            ["Viagens com CT-e - valor líquido após desconto", str(total_viagens_com_cte), f"R$ {valor_total_viagens_com_cte}"],
            ["Viagens sem CT-e", str(total_viagens_sem_cte), f"R$ {valor_total_viagens_sem_cte}"],
            ["Total de vales descontados", "-", f"- R$ {desconto_vales}"],
            ["Desconto fixo", "-", f"- R$ {desconto_fixo}"],
            [f"Comissão do motorista ({percentual_comissao}% sobre o valor líquido)", "-", f"R$ {comissao}"],
            ["VALOR A PAGAR AO MOTORISTA", "-", f"R$ {valor_a_receber}"],
        ]
        tabela_resumo = Table(resumo_dados, colWidths=[12*cm, 4*cm, 6*cm], repeatRows=1)
        tabela_resumo.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("TEXTCOLOR", (0,0), (-1,0), colors.black),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("GRID", (0,0), (-1,-1), 0.8, colors.black),
            ("ALIGN", (1,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("BACKGROUND", (0,-1), (-1,-1), colors.Color(0.87, 0.97, 0.89)),
            ("TEXTCOLOR", (0,-1), (-1,-1), colors.Color(0.05, 0.45, 0.15)),
            ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ]))
        elementos.append(tabela_resumo)

        doc.build(elementos, onFirstPage=draw_header, onLaterPages=draw_header)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="acerto_fretes_{motorista.nome}_{inicio}_{fim}.pdf"'
        )
        return response
