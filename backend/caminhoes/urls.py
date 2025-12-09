from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CaminhaoViewSet

router = DefaultRouter()
router.register(r'', CaminhaoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
