from django.urls import path
from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import ProfileView, ProfileEditView, CustomPasswordChangeView
from .views import (
    newsletter_campaign_list, newsletter_campaign_create, 
    newsletter_campaign_edit, newsletter_campaign_send,
    newsletter_campaign_preview, newsletter_campaign_delete,
    
)


urlpatterns = [
    #path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('create/', views.create_user_view, name='create_user'),

    path('list/', views.user_list_view, name='user_list'),
    path('<int:id>/', views.user_detail_view, name='user_detail'),
    path('create_member/', views.create_member_view, name='create_member'),

#08_08

    path('profil/', ProfileView.as_view(), name='profile'),
    path('profil/modifier/', ProfileEditView.as_view(), name='profile_edit'),
    path('profil/mot-de-passe/', CustomPasswordChangeView.as_view(), name='password_change'),

#08_08
#17_08
    path('update/<int:pk>/', views.update_user_view, name='update_user'),
    path('delete/<int:id>/', views.user_delete, name='user_delete'),
    path('newsletter/', views.newsletter_list, name='newsletter_list'),
    path('contact-messages/', views.contact_message_list, name='contact_message_list'),
    path('contact-messages-sent/', views.sent_messages_list, name='sent_messages_list'),
    path('contact-messages/<int:pk>/', views.contact_message_detail, name='contact_message_detail'),
    path('contact-messages/<int:pk>/delete/', views.contact_message_delete, name='contact_message_delete'),
    path('contact-messages/<int:pk>/reply/', views.contact_message_reply, name='contact_message_reply'),
    
    path('newsletter/campaigns/', newsletter_campaign_list, name='newsletter_campaign_list'),
    path('newsletter/campaigns/create/', newsletter_campaign_create, name='newsletter_campaign_create'),
    path('newsletter/campaigns/<int:pk>/edit/', newsletter_campaign_edit, name='newsletter_campaign_edit'),
    path('newsletter/campaigns/<int:pk>/send/', newsletter_campaign_send, name='newsletter_campaign_send'),
    path('newsletter/campaigns/<int:pk>/preview/', newsletter_campaign_preview, name='newsletter_campaign_preview'),
    path('newsletter/campaigns/<int:pk>/delete/', newsletter_campaign_delete, name='newsletter_campaign_delete'),

    path('adhesions/', views.membership_application_list, name='membership_application_list'),
    path('adhesions/<int:pk>/', views.membership_application_detail, name='membership_application_detail'),
    path('adhesions/<int:pk>/<str:action>/', views.membership_application_action, name='membership_application_action'),

    path("partenaires/", views.partenaire_list, name="partenaire_list"),
    path("partenaires/create/", views.partenaire_create, name="partenaire_create"),
    path("partenaires/<int:pk>/", views.partenaire_detail, name="partenaire_detail"),
    path("partenaires/<int:pk>/toggle/", views.partenaire_toggle, name="partenaire_toggle"), 

]