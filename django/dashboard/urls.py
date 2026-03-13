from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/forest-stats/', views.forest_stats_api, name='forest_stats_api'),
    path('api/graphs/', views.graphs_api, name='graphs_api'),
]