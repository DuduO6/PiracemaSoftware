from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import FretesError
from .serializers import FreteCalculatorSerializer
from .services.freight_calculator import calcular_frete
from .services.municipalities_service import MunicipalitiesService, MunicipalitiesServiceError


class CalcularFreteAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FreteCalculatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            resultado = calcular_frete(serializer.validated_data, user=request.user)
        except FretesError as exc:
            response_payload = {"detail": exc.message, "code": exc.code}
            if exc.extra:
                response_payload.update(exc.extra)
            return Response(response_payload, status=exc.status_code)

        return Response(resultado, status=status.HTTP_200_OK)


class MunicipiosAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "")
        try:
            service = MunicipalitiesService()
            municipios = service.search(query=query)
        except MunicipalitiesServiceError as exc:
            return Response(
                {
                    "results": [],
                    "detail": exc.message,
                    "code": exc.code,
                    "degraded": True,
                },
                status=status.HTTP_200_OK,
            )
        return Response({"results": municipios, "degraded": False}, status=status.HTTP_200_OK)
