from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Value, CharField
from .models import Article,Guelekan
from .forms import ArticleForm,GuelekanForm
from .media_library import list_media_files  
from django.conf import settings
from django.template.loader import render_to_string
from site_web.models import NewsletterSubscriber
from site_web.email_utils import send_newsletter_email

from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q
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
    'ouvrage': ArticleForm,
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
        'article_type': article_type
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
        'article_type': article.article_type
    })

# 📃 Liste des articles
# views.py
@login_required
def article_list(request):
    articles = Article.objects.all().order_by('-created_at')
    
    # Filtrage
    category = request.GET.get('category')
    status = request.GET.get('status')
    article_type = request.GET.get('type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search')
    
    if category:
        articles = articles.filter(category=category)
    
    if status:
        articles = articles.filter(status=status)
    
    if article_type:
        articles = articles.filter(article_type=article_type)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            articles = articles.filter(created_at__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            articles = articles.filter(created_at__date__lte=date_to)
        except ValueError:
            pass
    
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) | 
            Q(content__icontains=search_query) |
            Q(subtitle__icontains=search_query)
        )
    
    return render(request, 'articles/article_list.html', {
        'articles': articles,
      
        'status_choices': Article.STATUS_CHOICES,
        'article_types': Article.ARTICLE_TYPE_CHOICES,
        'selected_category': category,
        'selected_status': status,
        'selected_type': article_type,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    })


# 🔍 Détail d'un article
@login_required
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    return render(request, 'articles/article_detail.html', {'article': article})

# 🗑️ Supprimer un article
@login_required
def article_delete(request, slug):
    article = get_object_or_404(Article, slug=slug)

    if request.method == 'POST':
        article.delete()
        messages.success(request, "L'article a été supprimé avec succès.")
        return redirect('article_list')

    return render(request, 'articles/article_confirm_delete.html', {'article': article})

# articles/views.py
@login_required
def publish_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.is_published():
        article.status = 'published'
        article.publish_at = timezone.now()  # Date de publication actuelle
        article.save()
        # Envoyer une newsletter si configuré
        if settings.SEND_NEWSLETTER_ON_PUBLISH:
            send_content_published_newsletter(article, "Nouveau Article")

        messages.success(request, f"L'article « {article.title} » a été publié.")
    return redirect('article_detail', slug=slug)


@login_required
def unpublish_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if article.is_published():
        article.status = 'draft'
        article.publish_at = None  # Réinitialiser la date de publication
        article.save()
        messages.warning(request, f"L'article « {article.title} » a été dépublié.")
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
    while Guelekan.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{i}"
        i += 1
    return slug

@login_required
def guelekan_list(request):
    guelekans = Guelekan.objects.all().order_by('-created_at')
    return render(request, 'articles/guelekan_list.html', {
        'guelekans': guelekans,
        'status_classes': {
            'draft': 'text-warning',
            'published': 'text-success',
        }
    })


# articles/views.py
@login_required
def guelekan_create(request):
    if request.method == 'POST':
        form = GuelekanForm(request.POST, request.FILES)
        if form.is_valid():
           
            guelekan = form.save()
            
            messages.success(request, 'Séminaire créé avec succès!')
            return redirect('guelekan_detail', slug=guelekan.slug)
    else:
        form = GuelekanForm()
    
    return render(request, 'articles/guelekan_form.html', {'form': form})

@login_required
def guelekan_update(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    
    if request.method == 'POST':
        form = GuelekanForm(request.POST, request.FILES, instance=guelekan)
        if form.is_valid():
            
            guelekan = form.save()
            
            messages.success(request, 'Séminaire mis à jour!')
            return redirect('guelekan_detail', slug=guelekan.slug)
    else:
        form = GuelekanForm(instance=guelekan)
    
    return render(request, 'articles/guelekan_form.html', {
        'form': form,
        'guelekan': guelekan
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


@login_required
def guelekan_delete(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)

    if request.method == 'POST':
        guelekan.delete()
        messages.success(request, "Le Guelekan a été supprimé avec succès.")
        return redirect('guelekan_list')

    return render(request, 'articles/guelekan_confirm_delete.html', {'guelekan': guelekan})


@login_required
def unpublish_guelekan(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    if guelekan.is_published():
        guelekan.status = 'draft'
        guelekan.save()
        messages.warning(request, f"Le Guelekan « {guelekan.title} » a été dépublié.")
    return redirect('guelekan_detail', slug=slug)


@login_required
def publish_guelekan(request, slug):
    guelekan = get_object_or_404(Guelekan, slug=slug)
    if not guelekan.is_published():
        guelekan.status = 'published'
        guelekan.save()
        
        # Envoyer une newsletter si configuré
        if settings.SEND_NEWSLETTER_ON_PUBLISH:
            send_content_published_newsletter(guelekan, "Nouveau Guelekan")
            
        messages.success(request, f"Le Guelekan « {guelekan.title} » a été publié.")
    return redirect('guelekan_detail', slug=slug)


def send_content_published_newsletter(content, content_type):
    """Envoyer une newsletter pour un nouveau contenu publié"""
    subscribers = NewsletterSubscriber.objects.all()
    success_count = 0
    error_count = 0
    
    for subscriber in subscribers:
        try:
            # Créer le contenu HTML
            html_content = render_to_string('emails/content_published.html', {
                'content': content,
                'content_type': content_type,
                'unsubscribe_url': f"{settings.SITE_URL}/newsletter/unsubscribe/{subscriber.id}/"
            })
            
            # Envoyer l'email
            subject = f"{content_type} : {content.title}"
            if send_newsletter_email(subject, html_content, [subscriber.email]):
                success_count += 1
            else:
                error_count += 1
            
        except Exception as e:
            error_count += 1
            # Loguer l'erreur
            print(f"Erreur lors de l'envoi à {subscriber.email}: {e}")
    
    return success_count, error_count