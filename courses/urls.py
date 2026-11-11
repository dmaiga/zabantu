"""Adresses publiques bilingues (sous /zabantu/ et /en/zabantu/) : connexion commune, compte, espace participant,
page « Formations »."""
from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    # Connexion commune à tout le monde (équipe et participants) ; aiguillage côté serveur
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='participant_logout'),
    path('compte/connexion/', RedirectView.as_view(pattern_name='login', query_string=True), name='participant_login'),

    # Page publique
    path('formations/', views.training_list, name='training_list'),

    # Création du compte (participants uniquement) et mot de passe oublié
    path('compte/inscription/', views.signup, name='participant_signup'),
    path('compte/inscription/envoyee/', views.signup_done, name='participant_signup_done'),
    path('compte/confirmer/<uidb64>/<token>/', views.confirm, name='participant_confirm'),
    path('compte/mot-de-passe/', views.PasswordResetView.as_view(), name='participant_password_reset'),
    path('compte/mot-de-passe/envoye/', views.PasswordResetDoneView.as_view(), name='participant_password_reset_done'),
    path('compte/mot-de-passe/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(),
         name='participant_password_reset_confirm'),
    path('compte/mot-de-passe/termine/', views.PasswordResetCompleteView.as_view(),
         name='participant_password_reset_complete'),

    # Espace participant
    path('compte/', views.dashboard, name='participant_space'),
    path('compte/cours/', views.my_courses, name='participant_courses'),
    path('compte/cours/<int:pk>/', views.course_detail, name='participant_course'),
    path('compte/fichiers/<int:pk>/', views.course_file, name='participant_course_file'),
    path('compte/formations/', views.my_trainings, name='participant_trainings'),
    path('compte/formations/<int:pk>/inscription/', views.enroll, name='training_enroll'),
    path('compte/profil/', views.profile, name='participant_profile'),
    path('compte/profil/mot-de-passe/', views.password_change, name='participant_password'),
    path('compte/adhesion/', views.membership, name='participant_membership'),
]
