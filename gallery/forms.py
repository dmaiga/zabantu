from django import forms
from users.formsupport import SectionedFormMixin
from .models import Gallery, Photo

class GalleryForm(SectionedFormMixin, forms.ModelForm):
    sections = (('Galerie', ('title', 'description', 'cover_image')), ('Mise en avant', ('is_featured',)))
    class Meta:
        model = Gallery
        fields = ['title', 'description', 'cover_image', 'is_featured']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

  

import os

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class PhotoForm(forms.ModelForm):
    images = MultipleFileField(
        required=True,
        label="Images",
        help_text="Sélectionnez une ou plusieurs images. Maintenez Ctrl/Cmd pour en sélectionner plusieurs."
    )

    class Meta:
        model = Photo
        fields = [ 'gallery', 'is_standalone']
        widgets = {
          
            'gallery': forms.Select(attrs={'class': 'form-control'}),
            'is_standalone': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        help_texts = {
            'title': 'Si vide, le nom du fichier sera utilisé comme titre',
            'is_standalone': 'Cocher si ces photos ne doivent pas être associées à une galerie'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les galeries disponibles
        self.fields['gallery'].queryset = Gallery.objects.all()
        self.fields['gallery'].required = False
        
        # Réorganiser l'ordre des champs
        self.order_fields(['images', 'gallery', 'is_standalone'])

    def clean(self):
        cleaned_data = super().clean()
        gallery = cleaned_data.get('gallery')
        is_standalone = cleaned_data.get('is_standalone')
        
        # Validation: une photo ne peut pas être à la fois dans une galerie et standalone
        if gallery and is_standalone:
            raise forms.ValidationError(
                "Une photo ne peut pas être à la fois dans une galerie et indépendante."
            )
        
        return cleaned_data