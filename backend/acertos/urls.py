from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AcertoViewSet

router = DefaultRouter()
router.register(r'', AcertoViewSet, basename='acerto')

urlpatterns = router.urls