from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Motorista, Vale
from .serializers import MotoristaSerializer, ValeSerializer

class MotoristaViewSet(viewsets.ModelViewSet):
    serializer_class = MotoristaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Motorista.objects.filter(usuario=self.request.user)



class ValeViewSet(viewsets.ModelViewSet):
    serializer_class = ValeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vale.objects.filter(motorista__usuario=self.request.user)

