# intervenants/urls.py
from django.urls import path
from . import views


urlpatterns = [
    path('', views.intervenant_list, name='intervenant_list'),
    path('nouveau/', views.intervenant_create, name='intervenant_create'),
    path('<int:id>/', views.intervenant_detail, name='intervenant_detail'),
    path('<int:id>/modifier/', views.intervenant_update, name='intervenant_update'),
    path('<int:id>/supprimer/', views.intervenant_delete, name='intervenant_delete'),
]