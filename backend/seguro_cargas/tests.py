from decimal import Decimal

from django.test import SimpleTestCase

from .serializers import SeguroCargasCalculoSerializer
from .services.calculo_comercial import calcular_seguro_comercial
from .services.tabela_deslocamentos import buscar_taxa_deslocamento
from .services.xml_importer import parse_documento_fiscal_xml


class SeguroComercialTests(SimpleTestCase):
    def calcular(self, **overrides):
        parametros = {
            "origem": "SP",
            "destino": "MG",
            "valor_carga": "100000.00",
            "piso_minimo_antt": "5141.93",
        }
        parametros.update(overrides)
        return calcular_seguro_comercial(**parametros)

    def test_consulta_a_matriz_real_da_planilha_por_uf(self):
        taxa, modo, origem, destino = buscar_taxa_deslocamento("SP", "MG")
        self.assertEqual(taxa, Decimal("0.05"))
        self.assertEqual(modo, "origem-destino")
        self.assertEqual((origem, destino), ("sao_paulo", "minas_gerais"))

    def test_formula_comercial_e_distribuicao_50_50(self):
        resultado = self.calcular()
        self.assertEqual(resultado["planilha"]["valor_original"], "59.06")
        self.assertEqual(resultado["seguro"]["valor_final"], "124.12")
        self.assertFalse(resultado["seguro"]["piso_aplicado"])
        self.assertEqual(resultado["percentuais"]["rctrc"], "0.062060")
        self.assertEqual(resultado["percentuais"]["rcdc"], "0.062060")
        self.assertEqual(resultado["percentuais"]["seguro_reconstituido"], "124.12")
        self.assertTrue(resultado["percentuais"]["reproduz_exatamente"])

    def test_piso_comercial_de_trinta_reais(self):
        resultado = self.calcular(valor_carga="1000.00")
        self.assertEqual(resultado["seguro"]["valor_final"], "30.00")
        self.assertTrue(resultado["seguro"]["piso_aplicado"])

    def test_distribuicao_configuravel(self):
        resultado = self.calcular(proporcao_rctrc="70")
        self.assertEqual(resultado["percentuais"]["valor_alvo_rctrc"], "86.88")
        self.assertEqual(resultado["percentuais"]["valor_alvo_rcdc"], "37.24")
        self.assertEqual(resultado["percentuais"]["descricao"], "Distribuição comercial configurada")

    def test_precisao_baixa_expoe_diferenca_sem_afirmar_igualdade(self):
        resultado = self.calcular(precisao_percentual=2)
        self.assertEqual(resultado["percentuais"]["rctrc"], "0.06")
        self.assertEqual(resultado["percentuais"]["seguro_reconstituido"], "120.00")
        self.assertEqual(resultado["percentuais"]["diferenca_arredondamento"], "-4.12")
        self.assertFalse(resultado["percentuais"]["reproduz_exatamente"])

    def test_percentuais_manuais_sao_recalculados(self):
        resultado = self.calcular(
            percentual_rctrc_manual="0.080000",
            percentual_rcdc_manual="0.040000",
        )
        self.assertEqual(resultado["percentuais"]["origem"], "manual")
        self.assertEqual(resultado["percentuais"]["seguro_reconstituido"], "120.00")
        self.assertEqual(resultado["percentuais"]["diferenca_arredondamento"], "-4.12")

    def test_valor_final_inclui_margem_e_pedagio_separado(self):
        resultado = self.calcular(margem_adicional="200", pedagio="80.50", outras_despesas="19.45")
        self.assertEqual(resultado["valor_final"]["subtotal_sem_pedagio"], "5466.05")
        self.assertEqual(resultado["valor_final"]["pedagio"], "80.50")
        self.assertEqual(resultado["valor_final"]["outras_despesas"], "19.45")
        self.assertEqual(resultado["valor_final"]["total"], "5566.00")

    def test_valor_zero_e_ausente_sao_rejeitados(self):
        zero = SeguroCargasCalculoSerializer(data={"origem": "SP", "destino": "MG", "valor_carga": "0"})
        ausente = SeguroCargasCalculoSerializer(data={"origem": "SP", "destino": "MG"})
        self.assertFalse(zero.is_valid())
        self.assertFalse(ausente.is_valid())


class DocumentoFiscalXMLTests(SimpleTestCase):
    def test_importa_nfe(self):
        xml = b"""<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe"><NFe><infNFe>
        <emit><enderEmit><xMun>Sao Paulo</xMun><UF>SP</UF></enderEmit></emit>
        <dest><enderDest><xMun>Belo Horizonte</xMun><UF>MG</UF></enderDest></dest>
        <total><ICMSTot><vNF>100000.00</vNF></ICMSTot></total>
        <transp><vol><pesoB>25000.000</pesoB></vol></transp>
        </infNFe></NFe></nfeProc>"""
        resultado = parse_documento_fiscal_xml(xml)
        self.assertEqual(resultado["tipo_documento"], "NF-e")
        self.assertEqual(resultado["valor_carga"], "100000.00")
        self.assertEqual(resultado["peso_toneladas"], "25.000")
        self.assertEqual((resultado["uf_origem"], resultado["uf_destino"]), ("SP", "MG"))

    def test_importa_cte(self):
        xml = b"""<cteProc xmlns="http://www.portalfiscal.inf.br/cte"><CTe><infCte>
        <ide><xMunIni>Goiania</xMunIni><UFIni>GO</UFIni><xMunFim>Brasilia</xMunFim><UFFim>DF</UFFim></ide>
        <infCarga><vCarga>50000.50</vCarga><infQ><cUnid>01</cUnid><tpMed>PESO BRUTO</tpMed><qCarga>12000</qCarga></infQ></infCarga>
        </infCte></CTe></cteProc>"""
        resultado = parse_documento_fiscal_xml(xml)
        self.assertEqual(resultado["tipo_documento"], "CT-e")
        self.assertEqual(resultado["peso_toneladas"], "12.000")
        self.assertEqual(resultado["valor_carga"], "50000.50")
