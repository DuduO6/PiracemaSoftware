from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Acerto, ItemAcerto, ValeAcerto
from .serialzers import AcertoSerializer, AcertoListSerializer


class AcertoViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Acerto.objects.filter(usuario=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return AcertoListSerializer
        return AcertoSerializer