from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SeguroCargasCalculoSerializer
from .services.calculo_comercial import calcular_seguro_comercial
from .services.tabela_deslocamentos import LocalidadeSeguroError
from .services.xml_importer import parse_documento_fiscal_xml


class CalcularSeguroCargasAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SeguroCargasCalculoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = calcular_seguro_comercial(**serializer.validated_data)
        except (LocalidadeSeguroError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(resultado, status=status.HTTP_200_OK)


class ImportarDocumentoFiscalAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            return Response(
                {"detail": "Envie um arquivo XML de NF-e ou CT-e."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            resultado = parse_documento_fiscal_xml(arquivo.read())
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(resultado, status=status.HTTP_200_OK)

