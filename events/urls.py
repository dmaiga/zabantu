
from django.urls import path
from . import views

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('create/', views.event_create, name='event_create'),
    path('<int:id>/', views.event_detail, name='event_detail'),
    path('<int:id>/edit/', views.event_update, name='event_update'),
    path('<int:id>/delete/', views.event_delete, name='event_delete'),
    path('<int:id>/publish/', views.event_publish, name='event_publish'),
    path('<int:id>/unpublish/', views.event_unpublish, name='event_unpublish'),
    path('<int:id>/archive/', views.event_archive, name='event_archive'),

    path('<int:id>/intervenants/', views.manage_event_intervenants, name='manage_event_intervenants'),
    path('intervenant/<int:id>/delete/', views.remove_event_intervenant, name='remove_event_intervenant'),
]