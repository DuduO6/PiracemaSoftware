from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def home_dashboard(request):
    return Response({
        "faturamento": 1000000,
        "despesas": 30000,
        "lucro": 700000
    })
