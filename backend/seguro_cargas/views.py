from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SeguroCargasCalculoSerializer
from .services.calculo_seguro import calcular_seguro
from .services.tabela_deslocamentos import LocalidadeSeguroError


class CalcularSeguroCargasAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SeguroCargasCalculoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = calcular_seguro(**serializer.validated_data)
        except LocalidadeSeguroError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(resultado, status=status.HTTP_200_OK)

