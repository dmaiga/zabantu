from django.urls import path
from .views import (
    gallery_list, gallery_detail,
    photo_list, photo_detail,
    gallery_create, photo_create,
    gallery_update,
    gallery_delete,
    photo_update,
    photo_delete,
)


urlpatterns = [
    path('photos/', photo_list, name='photo_list'),
    path('photos/creer/', photo_create, name='photo_create'),
    path('photos/<int:pk>/', photo_detail, name='photo_detail'),
    path('photos/<int:pk>/modifier/', photo_update, name='photo_update'),
    path('photos/<int:pk>/supprimer/', photo_delete, name='photo_delete'),

    
    path('', gallery_list, name='gallery_list'),
    path('creer/', gallery_create, name='gallery_create'),
    path('<slug:slug>/', gallery_detail, name='gallery_detail'),
    path('<slug:slug>/modifier/', gallery_update, name='gallery_update'),
    path('<slug:slug>/supprimer/', gallery_delete, name='gallery_delete'),
    

]