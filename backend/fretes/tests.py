from django.test import SimpleTestCase

from decimal import Decimal

from fretes.services.geocoding_service import build_geocoding_cache_key
from fretes.services.antt_table_service import ANTTTableService, ANTT_TABLE_REFERENCE
from fretes.serializers import FreteCalculatorSerializer


class GeocodingCacheKeyTests(SimpleTestCase):
    def test_cache_key_is_memcached_safe_and_stable(self):
        key = build_geocoding_cache_key("  Carmo da Mata  ", "MG")
        self.assertEqual(key, build_geocoding_cache_key("carmo da mata", "mg"))
        self.assertNotIn(" ", key)
        self.assertNotIn("Carmo", key)
        self.assertLessEqual(len(key), 250)


class ANTTCalculationTests(SimpleTestCase):
    def test_aceita_peso_importado_do_xml_com_tres_casas(self):
        serializer = FreteCalculatorSerializer(data={
            "cidade_origem": "São Paulo",
            "estado_origem": "SP",
            "cidade_destino": "Belo Horizonte",
            "estado_destino": "MG",
            "peso_estimado_toneladas": "12.345",
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_calculo_preserva_coeficientes_e_referencia_vigente(self):
        service = ANTTTableService()
        coefficients = service.resolve_coefficients(
            tipo_carga="carga_geral",
            quantidade_eixos=6,
            composicao_veicular=True,
            alto_desempenho=False,
        )
        resultado = service.calcular_valores(
            distancia_km=Decimal("606.1438"),
            coefficients=coefficients,
            retorno_vazio=False,
        )
        self.assertEqual(coefficients["ccd"], Decimal("7.4124"))
        self.assertEqual(coefficients["cc"], Decimal("648.95"))
        self.assertEqual(resultado["valor_total"], Decimal("5141.93"))
        self.assertIn("Portaria SUROC nº 04/2026", ANTT_TABLE_REFERENCE)
