from django.urls import path
from django.views.generic import TemplateView
from .views import (
    HomeView, 
    public_article_list, 
    public_article_detail,
    public_event_list,
    public_event_detail,
    public_event_ics,
    public_member_list,
    public_member_detail,
    public_guelekan_list,
    public_guelekan_detail,
    about_view,    
    liste_galeries,
    detail_galerie,
    detail_photo,
    toutes_photos,
    contact,
    membership_apply,
    membership_thanks,
    newsletter_subscribe,
    newsletter_unsubscribe,
   

)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('publications/', public_article_list, name='public_article_list'),
    path('publications/<slug:slug>/', public_article_detail, name='public_article_detail'),
    
    path('evenements/', public_event_list, name='public_event_list'),
    path('evenements/<int:pk>/', public_event_detail, name='public_event_detail'),
    path('evenements/<int:pk>/calendrier.ics', public_event_ics, name='public_event_ics'),
    path('membres/', public_member_list, name='public_member_list'),
    path('membres/<int:pk>/', public_member_detail, name='public_member_detail'),
    # Guelekan
    path('guelekans/', public_guelekan_list, name='public_guelekan_list'),
    path('guelekans/<slug:slug>/', public_guelekan_detail, name='public_guelekan_detail'),
    #05_08
    path('about/', about_view, name='about'),
    #06_08
    
    path('contact/', contact, name='contact'),
    path('mentions-legales/', TemplateView.as_view(template_name='site_web/legal/legal_notice.html', extra_context={'legal_page': 'notice'}), name='legal_notice'),
    path('confidentialite/', TemplateView.as_view(template_name='site_web/legal/privacy.html', extra_context={'legal_page': 'privacy'}), name='privacy'),
    path('cookies/', TemplateView.as_view(template_name='site_web/legal/cookies.html', extra_context={'legal_page': 'cookies'}), name='cookies'),
    path('adhesion/', membership_apply, name='membership_apply'),
    path('adhesion/merci/', membership_thanks, name='membership_thanks'),
    
    path('galeries/', liste_galeries, name='liste_galeries'),
    path('galerie/<slug:slug>/', detail_galerie, name='detail_galerie'),
    path('photos/', toutes_photos, name='toutes_photos'),
    path('photo/<int:pk>/', detail_photo, name='detail_photo'),
   #16_08
    path('newsletter/subscribe/', newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/unsubscribe/<uuid:token>/', newsletter_unsubscribe, name='newsletter_unsubscribe'),
    

]
