from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from users.permissions import moderator_required
from django.contrib import messages
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Value, CharField
from .models import Article,Guelekan
from .forms import ArticleForm,GuelekanForm, OuvrageForm
from .filters import ArticleFilterForm, GuelekanFilterForm
from users.listing import paginate
from .media_library import list_media_files  
from django.conf import settings
from django.template.loader import render_to_string
from site_web.mailing import notify_publication

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Count, Q
from datetime import datetime


# Générateur de slug unique
def generate_unique_slug(title):
    base_slug = slugify(title)
    slug = base_slug
    i = 1
    while Article.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug

# 📁 Media Library
@login_required
def media_library(request):
    media_files = list_media_files()
    return render(request, 'articles/media_library.html', {'media_files': media_files})
# 📝 Créer un article
from .forms import ArticleForm, AcademicForm, IndependentForm, WorkingPaperForm

FORM_MAPPING = {
    'zabantu': ArticleForm,
    'analyse': ArticleForm,
    'article': ArticleForm,
    'policy': ArticleForm,
    'ouvrage': OuvrageForm,
    'rapport': ArticleForm,

    'academic': AcademicForm,
    'independent': IndependentForm,
    'working': WorkingPaperForm,
}

@login_required
def article_create(request):
    article_type = request.GET.get('type') or request.POST.get('article_type')

    if not article_type:
        return render(request, 'articles/select_type.html')

    form_class = FORM_MAPPING.get(article_type, ArticleForm)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES)

        if form.is_valid():
            article = form.save(commit=False)
            article.slug = generate_unique_slug(article.title)
            article.status = 'draft'
            article.article_type = article_type  
            article.save()
            form.save_m2m()

            messages.success(request, "Article créé avec succès!")
            return redirect('article_detail', slug=article.slug)

        else:
            messages.error(request, "Veuillez corriger les erreurs.")
    else:
        form = form_class(initial={'article_type': article_type})

    return render(request, 'articles/article_update.html', {
        'form': form,
        'article_type': article_type,
        'type_label': dict(Article.TYPE_MENU).get(article_type, article_type),
        'back_url': reverse('article_list'),
    })

@login_required
def article_update(request, slug):
    article = get_object_or_404(Article, slug=slug)

    if article.is_published() and not request.user.is_superuser:
        messages.error(request, "Les articles publiés ne peuvent plus être modifiés.")
        return redirect('article_detail', slug=article.slug)

    form_class = FORM_MAPPING.get(article.article_type, ArticleForm)

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=article)

        if form.is_valid():
            article = form.save(commit=False)
            article.save()
            form.save_m2m()

            messages.success(request, "Article mis à jour avec succès.")
            return redirect('article_detail', slug=article.slug)

        else:
            messages.error(request, "Veuillez corriger les erreurs.")
    else:
        form = form_class(instance=article)

    return render(request, 'articles/article_update.html', {
        'form': form,
        'is_edit': True,
        'article_type': article.article_type,
        'type_label': article.type_label,
        'article': article,
        'back_url': reverse('article_detail', args=[article.slug]),
    })

# 📃 Liste des articles
# views.py
@login_required
def article_list(request):
    form = ArticleFilterForm(request.GET)
    articles = form.apply(Article.objects.all().order_by('-created_at'))
    page_obj, querystring = paginate(request, articles)
    counts = {row['status']: row['n'] for row in Article.objects.values('status').annotate(n=Count('id'))}
    return render(request, 'articles/article_list.html', {
        'form': form,
        'page_obj': page_obj,
        'querystring': querystring,
        'article_types': Article.TYPE_MENU,
        'status_tabs': [(value, label, counts.get(value, 0)) for value, label in Article.STATUS_CHOICES],
        'total_count': sum(counts.values()),
        'current_status': form.cleaned_data.get('status', ''),
    })


# 🔍 Détail d'un article
@login_required
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'articles/article_detail.html', {'article': article})

# 🗑️ Supprimer un article
@moderator_required
def article_delete(request, slug):
    article = get_object_or_404(Article, slug=slug)

    if request.method == 'POST':
        article.delete()
        messages.success(request, "L'article a été supprimé avec succès.")
        return redirect('article_list')

    return render(request, 'articles/article_confirm_delete.html', {'article': article})

# articles/views.py
def _schedule(request, obj, label, redirect_name):
    """Programme la publication de `obj` à la date postée (datetime-local)."""
    when = parse_datetime(request.POST.get('publish_at', ''))
    if when is not None and timezone.is_naive(when):
        when = timezone.make_aware(when)
    if when is None or when <= timezone.now():
        messages.error(request, "Indiquez une date et une heure de publication dans le futur.")
    else:
        obj.status = 'scheduled'
        obj.publish_at = when
        obj.save()
        messages.success(request, f"{label} « {obj.title} » sera publié(e) le {timezone.localtime(when):%d/%m/%Y à %H:%M}.")
    return redirect(redirect_name, slug=obj.slug)


@require_POST
@moderator_required
def schedule_article(request, slug):
    return _schedule(request, get_object_or_404(Article, slug=slug), "La publication", 'article_detail')


@require_POST
@moderator_required
def schedule_guelekan(request, slug):
    return _schedule(request, get_object_or_404(Guelekan, slug=slug), "Le Gɛlɛkan", 'guelekan_detail')


@require_POST
@moderator_required
def publish_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.is_published():
        article.status = 'published'
        article.publish_at = timezone.now()  # Date de publication actuelle
        article.save()
        notify_publication(article)

        messages.success(request, f"L'article « {article.title} » a été publié.")
    return redirect('article_detail', slug=slug)


@require_POST
@moderator_required
def unpublish_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if article.status in ('published', 'scheduled'):
        article.status = 'draft'
        article.publish_at = None  # Réinitialiser la date de publication
        article.save()
        messages.warning(request, f"La publication « {article.title} » est repassée en brouillon.")
    return redirect('article_detail', slug=slug)

#
#---------------------------------------------------------
#                              Guelekan    
#________________________________________________________
#

def generate_guelekan_slug(title):
    base_slug = slugify(title)
    slug = base_slug
    i = 1
    while Gɛlɛkan.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug

@login_required
def guelekan_list(request):
    form = GuelekanFilterForm(request.GET)
    seminars = form.apply(Guelekan.objects.annotate(
        n_guests=Count('intervenants', distinct=True), n_galleries=Count('galleries', distinct=True),
    ).order_by('-created_at'))
    page_obj, querystring = paginate(request, seminars)
    counts = {row['status']: row['n'] for row in Guelekan.objects.values('status').annotate(n=Count('id'))}
    return render(request, 'articles/guelekan_list.html', {
        'form': form,
        'page_obj': page_obj,
        'querystring': querystring,
        'status_choices': Guelekan.STATUS_CHOICES,
        'counts': counts,
        'total_count': sum(counts.values()),
    })


# articles/views.py
@login_required
def guelekan_create(request):
    if request.method == 'POST':
        form = GuelekanForm(request.POST, request.FILES)
        if form.is_valid():
           
            guelekan = form.save()
            if guelekan.status == 'published':
                notify_publication(guelekan)

            messages.success(request, 'Séminaire créé avec succès!')
            return redirect('guelekan_detail', slug=guelekan.slug)
    else:
        form = GuelekanForm()
    
    return render(request, 'articles/guelekan_form.html', {'form': form, 'back_url': reverse('guelekan_list')})

@login_required
def guelekan_update(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    
    if request.method == 'POST':
        form = GuelekanForm(request.POST, request.FILES, instance=guelekan)
        if form.is_valid():
            
            guelekan = form.save()
            if guelekan.status == 'published':
                notify_publication(guelekan)

            messages.success(request, 'Séminaire mis à jour!')
            return redirect('guelekan_detail', slug=guelekan.slug)
    else:
        form = GuelekanForm(instance=guelekan)
    
    return render(request, 'articles/guelekan_form.html', {
        'form': form,
        'guelekan': guelekan,
        'back_url': reverse('guelekan_detail', args=[guelekan.slug]),
    })


@login_required
def guelekan_detail(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    
    # Récupérer toutes les galeries associées avec leurs photos
    galleries = guelekan.galleries.all().prefetch_related('photos')
    
    return render(request, 'articles/guelekan_detail.html', {
        'guelekan': guelekan,
        'galleries': galleries,
        'timezone': timezone
    })


@moderator_required
def guelekan_delete(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)

    if request.method == 'POST':
        guelekan.delete()
        messages.success(request, "Le Gɛlɛkan a été supprimé avec succès.")
        return redirect('guelekan_list')

    return render(request, 'articles/guelekan_confirm_delete.html', {'guelekan': guelekan})


@require_POST
@moderator_required
def unpublish_guelekan(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    if guelekan.status in ('published', 'scheduled'):
        guelekan.status = 'draft'
        guelekan.publish_at = None
        guelekan.save()
        messages.warning(request, f"Le Gɛlɛkan « {guelekan.title} » a été dépublié.")
    return redirect('guelekan_detail', slug=slug)


@require_POST
@moderator_required
def publish_guelekan(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    if not guelekan.is_published():
        guelekan.status = 'published'
        guelekan.save()
        notify_publication(guelekan)
        messages.success(request, f"Le Gɛlɛkan « {guelekan.title} » a été publié.")
    return redirect('guelekan_detail', slug=slug)
