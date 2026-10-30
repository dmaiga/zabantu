from django.urls import path
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
    membre_liste,
    membre_detail,
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
    path('membres/', membre_liste, name='membre_liste'),
    path('membres/<int:user_id>/', membre_detail, name='membre_detail'),
    
    path('contact/', contact, name='contact'),
    path('adhesion/', membership_apply, name='membership_apply'),
    path('adhesion/merci/', membership_thanks, name='membership_thanks'),
    
    path('galeries/', liste_galeries, name='liste_galeries'),
    path('galerie/<slug:slug>/', detail_galerie, name='detail_galerie'),
    path('photos/', toutes_photos, name='toutes_photos'),
    path('photo/<int:pk>/', detail_photo, name='detail_photo'),
   #16_08
    path('newsletter/subscribe/', newsletter_subscribe, name='newsletter_subscribe'),
    path('newsletter/unsubscribe/<int:subscriber_id>/', newsletter_unsubscribe, name='newsletter_unsubscribe'),
    

]
