from django.urls import path,include
from . import views

urlpatterns = [
    path('media-library/', views.media_library, name='media_library'),
    path('', views.article_list, name='article_list'),
    path('article/create/', views.article_create, name='article_create'),
    path('article/<slug:slug>/', views.article_detail, name='article_detail'),
    path('article/<slug:slug>/edit/', views.article_update, name='article_update'),
    path('article/<slug:slug>/delete/', views.article_delete, name='article_delete'),
    path('article/<slug:slug>/publish/', views.publish_article, name='publish_article'),
    path('article/<slug:slug>/unpublish/', views.unpublish_article, name='unpublish_article'),
    path('article/<slug:slug>/schedule/', views.schedule_article, name='schedule_article'),
    #--------------------------------------------------------------------------
    #
    #                                Guelekan URLs
    #___________________________________________________________________________
    
    path('guelekan/', views.guelekan_list, name='guelekan_list'),
    path('guelekan/create/', views.guelekan_create, name='guelekan_create'),
    path('guelekan/<slug:slug>/', views.guelekan_detail, name='guelekan_detail'),
    path('guelekan/<slug:slug>/edit/', views.guelekan_update, name='guelekan_update'),
    path('guelekan/<slug:slug>/delete/', views.guelekan_delete, name='guelekan_delete'),
    path('guelekan/<slug:slug>/publish/', views.publish_guelekan, name='publish_guelekan'),
    path('guelekan/<slug:slug>/unpublish/', views.unpublish_guelekan, name='unpublish_guelekan'),
    path('guelekan/<slug:slug>/schedule/', views.schedule_guelekan, name='schedule_guelekan'),

       path('summernote/', include('django_summernote.urls')),
]
