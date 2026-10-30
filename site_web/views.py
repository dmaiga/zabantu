from datetime import timedelta, timezone as dt_timezone
from urllib.parse import urlencode
from django.http import HttpResponse
from django.utils.formats import date_format
from django.utils.html import strip_tags
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from articles.models import Article,Guelekan
from events.models import Event
from gallery.models import Photo, Gallery, PhotoTag
from django.views.generic import TemplateView
from django.utils import timezone
from django.db.models import Count, Q, F, OuterRef, Subquery
from django.http import Http404
from users.models import CustomUser
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache



#09_08
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator

def public_member_detail(request, pk):
    """Détail d'un membre"""
    member = get_object_or_404(
        CustomUser,
        pk=pk,
        is_active=True,
        role__in=['moderateur', 'membre']
    )
    
    # Récupérer les articles publiés dont le membre est auteur
    articles = Article.objects.filter(
        authors=member,
        status='published'
    ).order_by('-publish_at')
    
    return render(request, 'site_web/public_member_detail.html', {
        'member': member,
        'articles': articles
    })

#09_08
#------------------------------------------------------------------------------
#06_08_2025
# views.py

from django.shortcuts import render, get_object_or_404
from users.models import CustomUser
from articles.models import Article

def membre_liste(request):
    # Récupérer tous les membres actifs
    membres = CustomUser.objects.filter(is_active=True).order_by('nom')
    
    # Préparer les données pour chaque membre
    membres_data = []
    for membre in membres:
        publications_recentes = Article.objects.filter(
            authors=membre,
            status='published'
        ).order_by('-publish_at')[:3]  # 3 publications les plus récentes
        
        membres_data.append({
            'membre': membre,
            'publications_count': Article.objects.filter(authors=membre, status='published').count(),
            'publications_recentes': publications_recentes,
        })
    
    context = {
        'membres': membres_data,
        'title': 'Notre équipe de recherche'
    }
    return render(request, 'site_web/public_membre_liste.html', context)

def membre_detail(request, user_id):
    membre = get_object_or_404(CustomUser, id=user_id, is_active=True)
    
    # Récupérer toutes les publications publiées du membre
    publications = Article.objects.filter(
        authors=membre,
        status='published'
    ).order_by('-publish_at')
    
    context = {
        'membre': membre,
        'publications': publications,
        'title': f'Profil de {membre.prenom} {membre.nom}'
    }
    return render(request, 'site_web/public_membre_detail.html', context)


# site_web/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContactForm, MembershipApplicationForm

def contact(request):
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()  # Enregistre dans la BD
            messages.success(request, "Merci ! Votre message a été enregistré ✅")
            return redirect('contact')  # recharge la page
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = ContactForm()
    
      # Coordonnées pour la carte
    map_embed_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3859.227623693815!2d-7.987846684716715!3d12.672381921394377!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x0%3A0x0!2zMTLCsDQwJzIwLjYiTiA3wrA1OScxNS4xIlc!5e1!3m2!1sfr!2sfr!4v1620000000000!5m2!1sfr!2sfr"

    context = {
        'form': form,  # ton formulaire
        'map_embed_url': map_embed_url,
        'page_title': "Contact - Zabantu",
        'social_links': {
            'linkedin': "https://www.linkedin.com/company/zabantu-ecs/about/",
            'facebook': "https://www.facebook.com/zabantu.ecs",
            'twitter': "#",
            'researchgate': "#"
        }
    }
    return render(request, 'site_web/public_contact.html', context)

def membership_apply(request):
    """Formulaire public de demande d'adhésion (assistant en plusieurs étapes)"""
    if request.method == 'POST':
        form = MembershipApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save()
            request.session['membership_thanks'] = application.full_name
            return redirect('membership_thanks')
        messages.error(request, "Veuillez corriger les erreurs signalées.")
        start_step = form.first_error_step()
    else:
        form = MembershipApplicationForm()
        start_step = 0
    return render(request, 'site_web/public_membership_form.html', {
        'form': form,
        'start_step': start_step,
        'page_title': "Adhésion - Zabantu",
    })

def membership_thanks(request):
    """Page de remerciement après l'envoi d'une demande d'adhésion"""
    name = request.session.pop('membership_thanks', '')
    return render(request, 'site_web/public_membership_thanks.html', {
        'name': name,
        'page_title': "Merci - Zabantu",
    })

def liste_galeries(request):
    """Liste des galeries (seules les galeries contenant des photos sont publiées)"""
    first_photo = Photo.objects.filter(gallery=OuterRef('pk')).order_by('-uploaded_at').values('image')[:1]
    galeries_list = (
        Gallery.objects
        .annotate(n_photos=Count('photos'), first_photo=Subquery(first_photo))
        .filter(n_photos__gt=0)
        .order_by('-is_featured', '-created_at')
    )
    galeries = Paginator(galeries_list, 12).get_page(request.GET.get('page'))

    return render(request, 'site_web/public_liste_galeries.html', {
        'galeries': galeries,
        'photos_total': Photo.objects.count(),
        'page_title': "Galerie photos"
    })

def detail_galerie(request, slug):
    """Affiche une galerie spécifique avec ses photos"""
    galerie = get_object_or_404(Gallery, slug=slug)
    photos = galerie.photos.all().order_by('-uploaded_at')
    photos_page = Paginator(photos, 24).get_page(request.GET.get('page'))

    return render(request, 'site_web/public_detail_galerie.html', {
        'galerie': galerie,
        'photos': photos_page,
        'photo_total': photos_page.paginator.count,
        'page_title': f"Galerie : {galerie.title}"
    })

def toutes_photos(request):
    """Toutes les photos du site, filtrables par galerie et par mot-clé"""
    photos_list = Photo.objects.select_related('gallery').order_by('-uploaded_at')

    gallery_slug = request.GET.get('gallery', '')
    tag_slug = request.GET.get('tag', '')
    if gallery_slug:
        photos_list = photos_list.filter(gallery__slug=gallery_slug)
    if tag_slug:
        photos_list = photos_list.filter(tags__slug=tag_slug)

    photos = Paginator(photos_list, 36).get_page(request.GET.get('page'))

    return render(request, 'site_web/public_toutes_photos.html', {
        'photos': photos,
        'gallery_filters': Gallery.objects.annotate(n=Count('photos')).filter(n__gt=0).order_by('title'),
        'tag_filters': PhotoTag.objects.annotate(n=Count('photo')).filter(n__gt=0).order_by('name'),
        'current_gallery': gallery_slug,
        'current_tag': tag_slug,
        'page_title': "Toutes les photos"
    })

def detail_photo(request, pk):
    """Détail d'une photo, avec navigation vers la précédente et la suivante"""
    photo = get_object_or_404(Photo.objects.select_related('gallery', 'uploaded_by'), pk=pk)
    siblings = Photo.objects.filter(gallery=photo.gallery) if photo.gallery_id else Photo.objects.all()
    return render(request, 'site_web/public_detail_photo.html', {
        'photo': photo,
        'newer_photo': siblings.filter(uploaded_at__gt=photo.uploaded_at).order_by('uploaded_at').first(),
        'older_photo': siblings.filter(uploaded_at__lt=photo.uploaded_at).order_by('-uploaded_at').first(),
        'page_title': f"Photo : {photo.title}"
    })
#06_08_2025
#------------------------------------------------------------------------------
#Start with public gallery 
#Contact
#membres
#------------------------------------------------------------------------------
#05_08_2025

from django.contrib.auth import get_user_model
import random
from users.models import Partenaire
User = get_user_model()

def about_view(request):
    # Récupérer tous les membres actifs
    active_members = list(User.objects.filter(
        is_active=True,
        role__in=['moderateur', 'membre']
    ))
    
    # Sélectionner 4 membres aléatoires si on en a assez
    if len(active_members) > 4:
        active_members = random.sample(active_members, 4)
    else:
        # Si moins de 4 membres, prendre tous les membres disponibles
        active_members = active_members[:4]
    partenaires = Partenaire.objects.filter(is_active=True).order_by('order')
    context = {
        'active_members': active_members,
        'partenaires': partenaires,
    }
    return render(request, 'site_web/public_about.html', context)



#05_08
#______________________________________________________________________________
CATEGORY_LABELS = {
    'zabantu': 'Zabantu',
    'analyse': 'Analyses',
    'article': 'Articles',
    'policy': 'Policy Briefs',
    'ouvrage': 'Ouvrages',
    'rapport': 'Rapports',
    'academic': 'Publications académiques',
    'independent': 'Publications indépendantes',
    'working': 'Working Papers',
}


def public_article_list(request):
    current_filter = request.GET.get('type')
    search_query = request.GET.get('q')
    sort_option = request.GET.get('sort', 'date_desc')

    guelekan_qs = Guelekan.objects.filter(status='published')
    guelekan_count = guelekan_qs.count()

    # Gɛlɛkan est un filtre de la page Publications : même liste, même carte
    if current_filter == 'guelekan':
        if search_query:
            guelekan_qs = guelekan_qs.filter(
                Q(title__icontains=search_query) |
                Q(subtitle__icontains=search_query) |
                Q(content__icontains=search_query)
            )
        guelekan_qs = guelekan_qs.order_by(F('publish_at').desc(nulls_last=True), '-created_at')
        page_obj = Paginator(guelekan_qs, 12).get_page(request.GET.get('page'))
        total_articles = Article.objects.filter(status='published').count()
        type_counts_qs = Article.objects.filter(status='published').values('article_type').annotate(count=Count('id'))
        type_counts = {item['article_type']: item['count'] for item in type_counts_qs}
        return render(request, 'site_web/public_article_list.html', {
            'articles': [],
            'guelekans': page_obj,
            'page_obj': page_obj,
            'current_filter': current_filter,
            'search_query': search_query or '',
            'guelekan_count': guelekan_count,
            'category_data': [(k, CATEGORY_LABELS[k], type_counts.get(k, 0)) for k in CATEGORY_LABELS],
            'total_count': total_articles,
        })

    articles = Article.objects.filter(status='published')

    # ✅ FILTRE TYPE (clean)
    if current_filter:
        articles = articles.filter(article_type=current_filter)

    # ✅ SEARCH (corrigé multi-type)
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(subtitle__icontains=search_query) |
            Q(resume__icontains=search_query) |
            Q(abstract__icontains=search_query)
        )

    # ✅ SORT
    if sort_option == 'date_asc':
        articles = articles.order_by('created_at')
    elif sort_option == 'title_asc':
        articles = articles.order_by('title')
    elif sort_option == 'title_desc':
        articles = articles.order_by('-title')
    else:
        articles = articles.order_by('-created_at')

    # ✅ COUNTS PAR TYPE
    type_counts_qs = Article.objects.filter(status='published') \
        .values('article_type') \
        .annotate(count=Count('id'))

    type_counts = {item['article_type']: item['count'] for item in type_counts_qs}

    category_data = [
        (key, CATEGORY_LABELS[key], type_counts.get(key, 0))
        for key in CATEGORY_LABELS
    ]

    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'site_web/public_article_list.html', {
        'articles': page_obj,
        'page_obj': page_obj,
        'guelekan_count': guelekan_count,
        'current_filter': current_filter,
        'search_query': search_query or '',
        'category_data': category_data,
        'total_count': sum(type_counts.values()),
        'is_paginated': paginator.num_pages > 1,
    })

def public_article_detail(request, slug):
    article = get_object_or_404(
        Article, 
        slug=slug, 
        status='published'
    )
    
    if article.publish_at and article.publish_at > timezone.now():
        raise Http404("Cet article n'est pas encore publié")
    
    authors = article.authors.all()
    
    # Préparer les données spécifiques selon le type d'article
    context = {
        'article': article,
        'authors': authors,
    }
    
    return render(request, 'site_web/public_article_detail.html', context)


from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from events.models import Event, EventIntervenant
def _event_when(event):
    """Date de l'événement lisible : « 12 mai 2026 · 09:00 – 17:00 »."""
    start = timezone.localtime(event.date)
    day = date_format(start, "j F Y")
    if not event.end_date:
        return f"{day} · {date_format(start, 'H:i')}"
    end = timezone.localtime(event.end_date)
    if end.date() == start.date():
        return f"{day} · {date_format(start, 'H:i')} – {date_format(end, 'H:i')}"
    return f"{day} {date_format(start, 'H:i')} → {date_format(end, 'j F Y H:i')}"


def public_event_list(request):
    """Liste des événements publics : à venir, puis passés (paginés)"""
    now = timezone.now()
    published = Event.objects.filter(status='published')
    type_choices = dict(Event.EVENT_TYPE_CHOICES)

    current_type = request.GET.get('type')
    if current_type not in type_choices:
        current_type = ''

    upcoming_events = published.filter(date__gte=now).order_by('date')
    past_qs = published.filter(date__lt=now).order_by('-date')
    if current_type:
        upcoming_events = upcoming_events.filter(event_type=current_type)
        past_qs = past_qs.filter(event_type=current_type)

    past_events = Paginator(past_qs, 9).get_page(request.GET.get('page'))

    counts = {item['event_type']: item['n'] for item in published.values('event_type').annotate(n=Count('id'))}
    type_filters = [(key, label, counts.get(key, 0)) for key, label in Event.EVENT_TYPE_CHOICES if counts.get(key)]

    return render(request, 'site_web/public_event_list.html', {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'current_type': current_type,
        'type_filters': type_filters,
        'total_events': published.count(),
    })

def public_event_detail(request, pk):
    """Détail d'un événement public"""
    event = get_object_or_404(
        Event, 
        pk=pk,
        status='published'  
    )
    
    # Récupérer les intervenants avec leurs rôles
    event_intervenants = EventIntervenant.objects.filter(event=event).select_related('intervenant')
    
    # Grouper les intervenants par rôle
    intervenants_par_role = {}
    for event_intervenant in event_intervenants:
        role = event_intervenant.get_role_display()
        if role not in intervenants_par_role:
            intervenants_par_role[role] = []
        intervenants_par_role[role].append(event_intervenant.intervenant)
    
    now = timezone.now()
    is_past_event = event.date < now

    # Événements similaires (même type) : les plus récents d'abord
    similar_events = Event.objects.filter(
        status='published',  
        event_type=event.event_type
    ).exclude(pk=event.pk).order_by('-date')[:3]

    # Lien « Ajouter à Google Agenda »
    start_utc = event.date.astimezone(dt_timezone.utc)
    end_utc = (event.end_date or event.date + timedelta(hours=2)).astimezone(dt_timezone.utc)
    google_calendar_url = "https://calendar.google.com/calendar/render?" + urlencode({
        'action': 'TEMPLATE',
        'text': event.title,
        'dates': f"{start_utc:%Y%m%dT%H%M%SZ}/{end_utc:%Y%m%dT%H%M%SZ}",
        'details': strip_tags(event.content or '')[:400] + "\n" + request.build_absolute_uri(),
        'location': event.location or '',
    })

    return render(request, 'site_web/public_event_detail.html', {
        'event': event,
        'now': now,
        'time_range': _event_when(event),
        'is_past_event': is_past_event,
        'google_calendar_url': google_calendar_url,
        'intervenants_par_role': intervenants_par_role,
        'event_intervenants': event_intervenants,
        'similar_events': similar_events,
    })


def _ics_escape(text):
    return (text.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
                .replace('\r\n', '\\n').replace('\n', '\\n'))


def public_event_ics(request, pk):
    """Fichier .ics pour ajouter l'événement à n'importe quel agenda"""
    event = get_object_or_404(Event, pk=pk, status='published')
    start = event.date.astimezone(dt_timezone.utc)
    end = (event.end_date or event.date + timedelta(hours=2)).astimezone(dt_timezone.utc)
    description = strip_tags(event.content or '')[:500]
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Zabantu//Evenements//FR', 'CALSCALE:GREGORIAN',
        'BEGIN:VEVENT',
        f'UID:event-{event.pk}@zabantu',
        f'DTSTAMP:{timezone.now().astimezone(dt_timezone.utc):%Y%m%dT%H%M%SZ}',
        f'DTSTART:{start:%Y%m%dT%H%M%SZ}',
        f'DTEND:{end:%Y%m%dT%H%M%SZ}',
        f'SUMMARY:{_ics_escape(event.title)}',
        f'DESCRIPTION:{_ics_escape(description)}',
        f'LOCATION:{_ics_escape(event.location or "")}',
        f'URL:{request.build_absolute_uri(reverse("public_event_detail", args=[event.pk]))}',
        'END:VEVENT', 'END:VCALENDAR',
    ]
    response = HttpResponse('\r\n'.join(lines) + '\r\n', content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="evenement-{event.pk}.ics"'
    return response

def public_member_list(request):
    """Liste des membres publics"""
    members = CustomUser.objects.filter(
        is_active=True,
        role__in=['moderateur', 'membre']
    ).order_by('last_name')
    
    return render(request, 'site_web/public_member_list.html', {
        'members': members
    })

class HomeView(TemplateView):
    template_name = 'site_web/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        published_articles = Article.objects.filter(status='published')
        # Dernières publications : par date de publication (création à défaut)
        context['latest_articles'] = published_articles.order_by(
            F('publish_at').desc(nulls_last=True), '-created_at')[:4]

        # Événements à venir
        context['upcoming_events'] = Event.objects.filter(
            status='published',
            date__gte=timezone.now()
        ).order_by('date')[:3]

        # Membres actifs : aperçu de l'équipe et compteur
        members = CustomUser.objects.filter(is_active=True, role__in=['moderateur', 'membre'])
        context['team_members'] = members.order_by('-date_joined')[:4]

        # Chiffres clés (seules les valeurs non nulles sont affichées)
        context['stats'] = [
            ('Publications', published_articles.count(), 'fa-file-lines'),
            ('Membres', members.count(), 'fa-users'),
            ('Séminaires Gɛlɛkan', Guelekan.objects.filter(status='published').count(), 'fa-microphone-lines'),
            ('Événements', Event.objects.filter(status='published').count(), 'fa-calendar-days'),
        ]

        context['partenaires'] = Partenaire.objects.filter(is_active=True).order_by('order')
        return context


from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from articles.models import Guelekan

def public_guelekan_list(request):
    """Gɛlɛkan est désormais un filtre de la page Publications."""
    return redirect(f"{reverse('public_article_list')}?type=guelekan")


from django.db.models import Count

def public_guelekan_detail(request, slug):
    guelekan = get_object_or_404(
        Guelekan, 
        slug=slug, 
        status='published',
    )
    
    
    galleries = guelekan.galleries.all().prefetch_related('photos').annotate(
        annotated_photo_count=Count("photos")  
    )
    
    context = {
        'guelekan': guelekan,
        'galleries': galleries,
    }
    
    return render(request, 'site_web/public_guelekan_detail.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import NewsletterSubscriber
from django.contrib import messages

def newsletter_unsubscribe(request, subscriber_id):
    """Vue pour gérer le désabonnement de la newsletter"""
    subscriber = get_object_or_404(NewsletterSubscriber, id=subscriber_id)
    
    if request.method == 'POST':
        # Désabonnement confirmé
        subscriber.is_active = False
        subscriber.save()
        return render(request, 'site_web/newsletter_unsubscribe_success.html')
    
    # Afficher la page de confirmation de désabonnement
    return render(request, 'site_web/newsletter_unsubscribe_confirm.html', {
        'subscriber': subscriber
    })

def newsletter_subscribe(request):
    """Vue pour s'abonner à la newsletter"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # Vérifier si l'email existe déjà
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            
            if not created:
                # Réactiver l'abonné s'il existait déjà
                subscriber.is_active = True
                subscriber.save()
            
            messages.success(request, 'Vous êtes maintenant abonné à notre newsletter!')
            return redirect('home')
    
    return redirect('home')