from rest_framework import viewsets, permissions
from .models import Viagem, Motorista, Vale
from .serializers import ViagemSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime
from io import BytesIO
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
from acertos.models import Acerto, ItemAcerto, ValeAcerto


class ViagemViewSet(viewsets.ModelViewSet):
    serializer_class = ViagemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Viagem.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):
        peso = serializer.validated_data.get('peso', 0)
        valor_tonelada = serializer.validated_data.get('valor_tonelada', 0)
        valor_total = peso * valor_tonelada
        serializer.save(usuario=self.request.user, valor_total=valor_total)

    @action(detail=False, methods=['get'])
    def gerar_acerto(self, request):
        motorista_id = request.query_params.get('motorista_id')
        inicio = request.query_params.get('inicio')
        fim = request.query_params.get('fim')
        salvar = request.query_params.get('salvar', 'false').lower() == 'true'

        inicio_date = datetime.strptime(inicio, "%Y-%m-%d").date()
        fim_date = datetime.strptime(fim, "%Y-%m-%d").date()

        motorista = Motorista.objects.get(id=motorista_id, usuario=request.user)

        viagens = self.get_queryset().filter(
            motorista_id=motorista_id,
            data__gte=inicio_date,
            data__lte=fim_date
        ).order_by('data')

        vales = Vale.objects.filter(
            motorista_id=motorista_id,
            pago=False
        )

        total_valor = sum(v.valor_total for v in viagens)
        total_vales = sum(v.valor for v in vales)
        comissao = total_valor * Decimal("0.13")
        total_viagens = viagens.count()
        valor_a_receber = comissao - total_vales

        # SALVAR HISTÓRICO DE ACERTO
        if salvar:
            acerto = Acerto.objects.create(
                usuario=request.user,
                motorista=motorista,
                data_inicio=inicio_date,
                data_fim=fim_date,
                total_viagens=total_viagens,
                valor_total_viagens=total_valor,
                total_vales=total_vales,
                comissao=comissao,
                valor_a_receber=valor_a_receber
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
            f"<b>Período:</b> {inicio} até {fim}<br/>"
            f"<b>Total de viagens:</b> {total_viagens}",
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
            f"<b>TOTAL DE VALES:</b> R$ {total_vales}<br/>"
            f"<b>COMISSÃO (13%):</b> R$ {comissao}"
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