from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from users.permissions import moderator_required
from .models import Gallery, Photo
from .forms import GalleryForm, PhotoForm

# Vues publiques
def gallery_list(request):
    galleries = Gallery.objects.all().prefetch_related('photos')
    paginator = Paginator(galleries, 12)
    page_number = request.GET.get('page')
    galleries = paginator.get_page(page_number)
    return render(request, 'gallery/gallery_list.html', {'galleries': galleries})

def gallery_detail(request, slug):
    gallery = get_object_or_404(Gallery, slug=slug)
    photos = gallery.photos.all().order_by('-uploaded_at')
    return render(request, 'gallery/gallery_detail.html', {
        'gallery': gallery,
        'photos': photos
    })

def photo_list(request):
    photos = Photo.objects.filter(is_standalone=True).order_by('-uploaded_at')
    paginator = Paginator(photos, 24)
    page_number = request.GET.get('page')
    photos = paginator.get_page(page_number)
    return render(request, 'gallery/photo_list.html', {'photos': photos})

def photo_detail(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    return render(request, 'gallery/photo_detail.html', {'photo': photo})

# Vues CRUD Galerie
@login_required
def gallery_create(request):
    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES)
        if form.is_valid():
            gallery = form.save(commit=False)
            gallery.created_by = request.user
            gallery.save()
            messages.success(request, 'Galerie créée avec succès!')
            return redirect('gallery_detail', slug=gallery.slug)
    else:
        form = GalleryForm()
    
    return render(request, 'gallery/gallery_form.html', {'form': form, 'back_url': reverse('gallery_list')})

@login_required
@login_required
def gallery_update(request, slug):
    gallery = get_object_or_404(Gallery, slug=slug)

    # Le créateur, les modérateurs et les administrateurs peuvent modifier une galerie
    if not (request.user == gallery.created_by or request.user.can_moderate):
        messages.error(request, "Permission refusée")
        return redirect('gallery_detail', slug=slug)
    
    if request.method == 'POST':
        form = GalleryForm(request.POST, request.FILES, instance=gallery)
        if form.is_valid():
            form.save()
            messages.success(request, 'Galerie mise à jour!')
            return redirect('gallery_detail', slug=gallery.slug)
    else:
        form = GalleryForm(instance=gallery)
    
    return render(request, 'gallery/gallery_form.html', {
        'form': form,
        'gallery': gallery,
        'is_update': True,
        'back_url': reverse('gallery_detail', args=[gallery.slug]),
    })

@moderator_required
def gallery_delete(request, slug):
    gallery = get_object_or_404(Gallery, slug=slug)
    
    if request.method == 'POST':
        gallery.delete()
        messages.success(request, 'Galerie supprimée!')
        return redirect('gallery_list')
    
    return render(request, 'gallery/gallery_confirm_delete.html', {'gallery': gallery})

# Vues CRUD Photo
import os
from django.core.exceptions import ValidationError
from zabantu.validators import validate_image


def _image_errors(files):
    """Messages d'erreur des fichiers refusés (le téléversement multiple ne passe pas par un champ de formulaire)."""
    errors = []
    for f in files:
        try:
            validate_image(f)
        except ValidationError as e:
            errors.append(f"{f.name} : {e.messages[0]}")
    return errors


@login_required
def photo_create(request):
    gallery_id = request.GET.get('gallery')
    initial = {'gallery': gallery_id} if gallery_id else {}

    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES)
        files = request.FILES.getlist('images')  # ← Changer 'image' par 'images'

        file_errors = _image_errors(files)
        for error in file_errors:
            messages.error(request, error)

        if form.is_valid() and files and not file_errors:
            gallery = form.cleaned_data.get('gallery')
            title = form.cleaned_data.get('title')
            is_standalone = form.cleaned_data.get('is_standalone')

            photos_created = 0
            for f in files:
                # Utiliser le nom du fichier comme titre si aucun titre n'est fourni
                photo_title = title or os.path.splitext(f.name)[0]
                
                Photo.objects.create(
                    title=photo_title,
                    image=f,
                    gallery=gallery,
                    is_standalone=is_standalone,
                    uploaded_by=request.user
                )
                photos_created += 1
            
            messages.success(request, f'{photos_created} photo(s) ajoutée(s)!')

            if gallery and hasattr(gallery, 'slug') and gallery.slug:
                return redirect('gallery_detail', slug=gallery.slug)
            else:
                return redirect('photo_list')
        else:
            if not files:
                messages.error(request, 'Veuillez sélectionner au moins une image.')
    else:
        form = PhotoForm(initial=initial)

    return render(request, 'gallery/photo_form.html', {'form': form})

@login_required
def photo_update(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    
    # Autoriser l'admin/staff ou l'auteur à modifier
    if not (request.user == photo.uploaded_by or request.user.is_staff):
        messages.error(request, "Permission refusée")
        return redirect('photo_detail', pk=pk)
    
    if request.method == 'POST':
        form = PhotoForm(request.POST, request.FILES, instance=photo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Photo mise à jour!')
            
            if photo.gallery:
                return redirect('gallery_detail', slug=photo.gallery.slug)
            return redirect('photo_detail', pk=photo.pk)
    else:
        form = PhotoForm(instance=photo)
    
    return render(request, 'gallery/photo_form.html', {
        'form': form,
        'photo': photo,
        'is_update': True
    })

@moderator_required
def photo_delete(request, pk):
    photo = get_object_or_404(Photo, pk=pk)
    
    if request.method == 'POST':
        gallery_slug = photo.gallery.slug if photo.gallery else None
        photo.delete()
        messages.success(request, 'Photo supprimée!')
        
        if gallery_slug:
            return redirect('gallery_detail', slug=gallery_slug)
        return redirect('photo_list')
    
    return render(request, 'gallery/photo_confirm_delete.html', {'photo': photo})


