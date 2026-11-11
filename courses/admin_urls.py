"""Backoffice des formations (sous /courses/, modérateurs)."""
from django.urls import path

from . import admin_views as v

urlpatterns = [
    path('', v.course_list, name='course_admin_list'),
    path('cours/nouveau/', v.course_create, name='course_admin_create'),
    path('cours/<int:pk>/', v.course_detail, name='course_admin_detail'),
    path('cours/<int:pk>/modifier/', v.course_update, name='course_admin_update'),
    path('cours/<int:pk>/supprimer/', v.course_delete, name='course_admin_delete'),
    path('fichiers/<int:pk>/modifier/', v.course_file_update, name='course_file_admin_update'),
    path('fichiers/<int:pk>/supprimer/', v.course_file_delete, name='course_file_admin_delete'),

    path('cohortes/', v.cohort_list, name='cohort_admin_list'),
    path('cohortes/nouvelle/', v.cohort_create, name='cohort_admin_create'),
    path('cohortes/<int:pk>/', v.cohort_detail, name='cohort_admin_detail'),
    path('cohortes/<int:pk>/modifier/', v.cohort_update, name='cohort_admin_update'),
    path('cohortes/<int:pk>/supprimer/', v.cohort_delete, name='cohort_admin_delete'),
    path('cohortes/<int:pk>/activation/', v.cohort_toggle, name='cohort_admin_toggle'),
    path('cohortes/<int:pk>/annoncer/', v.cohort_announce, name='cohort_admin_announce'),
    path('cohortes/<int:pk>/inscriptions/', v.enrollment_bulk, name='enrollment_admin_bulk'),
    path('inscriptions/<int:pk>/<str:action>/', v.enrollment_action, name='enrollment_admin_action'),

    path('participants/', v.participant_list, name='participant_admin_list'),
    path('participants/<int:pk>/', v.participant_detail, name='participant_admin_detail'),
]
