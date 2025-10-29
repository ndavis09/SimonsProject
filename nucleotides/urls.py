from django.urls import path
from .views import HomeView, FetchDetailView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("doc/<int:pk>/", FetchDetailView.as_view(), name="fetch-detail"),
]
