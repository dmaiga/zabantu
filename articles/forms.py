# articles/forms.py
from django import forms
from tinymce.widgets import TinyMCE
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget
from .models import Article
from users.models import CustomUser
from users.models import CustomUser
from intervenants.models import Intervenant
from .models import Guelekan
from gallery.models import  Gallery


#09_08
class BaseArticleForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            # fichiers
            if isinstance(field.widget, forms.FileInput):
                field.widget.attrs.update({'class': 'form-control'})

            # textarea / summernote
            elif isinstance(field.widget, SummernoteWidget):
                continue

            # select multiple (authors)
            elif isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs.update({'class': 'form-select'})

            else:
                field.widget.attrs.update({'class': 'form-control'})

    class Meta:
        model = Article
        fields = ['title', 'cover_image', 'pdf_file']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            if isinstance(field.widget, forms.SelectMultiple):
                field.widget.attrs.update({'class': 'form-select'})

                # 🔥 FILTRAGE DES AUTEURS
                if name == 'authors':
                    field.queryset = CustomUser.objects.exclude(role='admin')

class ArticleForm(BaseArticleForm):
    content = forms.CharField(widget=SummernoteWidget(), required=True)

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'subtitle',
            'authors',
            'external_author',
            'content',
        ]

    def clean_authors(self):
        authors = self.cleaned_data.get('authors')
        if not authors:
            raise forms.ValidationError("Au moins un auteur interne est requis.")
        return authors
    
class AcademicForm(BaseArticleForm):
    abstract = forms.CharField(widget=SummernoteWidget(), label="Résumé")

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'authors',
            'academic_authors',
            'publication_year',
            'journal',
            'publisher',
            'external_link_academique',
            'abstract'
        ]

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get('publication_year'):
            self.add_error('publication_year', "Année obligatoire")

        if not cleaned_data.get('journal'):
            self.add_error('journal', "Journal obligatoire")

        if not cleaned_data.get('authors') and not cleaned_data.get('academic_authors'):
            raise forms.ValidationError("Au moins un auteur requis")

        return cleaned_data
   
class IndependentForm(BaseArticleForm):
    resume = forms.CharField(widget=SummernoteWidget(), required=True)

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'external_author',
            'external_link',
            'resume', 
        ]

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get('external_author'):
            self.add_error('external_author', "Auteur requis")

        if not cleaned_data.get('external_link'):
            self.add_error('external_link', "Lien requis")

        return cleaned_data
    
class WorkingPaperForm(BaseArticleForm):
    resume = forms.CharField(widget=SummernoteWidget(), required=True)

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'institution',
            'working_number',
            'working_series',
            'working_year',
            'resume',
            'authors',
            'academic_authors',
        ]

    def clean(self):
        cleaned_data = super().clean()

        if not cleaned_data.get('institution'):
            self.add_error('institution', "Institution requise")

        if not cleaned_data.get('working_number'):
            self.add_error('working_number', "Numéro requis")

        if not cleaned_data.get('working_year'):
            self.add_error('working_year', "Année requise")

        if not cleaned_data.get('authors') and not cleaned_data.get('academic_authors'):
            raise forms.ValidationError("Auteur requis")

        return cleaned_data

#________________________________________________________________
# articles/forms.py


class GuelekanForm(forms.ModelForm):
    content = forms.CharField(
        widget=TinyMCE(
            attrs={
                'cols': 80,
                'rows': 20,
                'plugins': 'preview autolink visualblocks image media table help',
                'toolbar': 'undo redo | styles | bold italic | alignleft aligncenter alignright | bullist numlist outdent indent | link image | preview media | help',
            }
        ),
        required=True,
        label="Contenu"
    )

    class Meta:
        model = Guelekan
        fields = [
            'title', 'subtitle', 'content', 'status', 'cover_image', 
            'pdf_file', 'galleries', 'intervenants', 'publish_at'
        ]
        widgets = {
            'publish_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'galleries': forms.SelectMultiple(attrs={'class': 'select2'}),
            'intervenants': forms.SelectMultiple(attrs={'class': 'select2'}),
            'subtitle': forms.TextInput(attrs={'placeholder': 'Sous-titre facultatif...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].initial = 'draft'
        self.fields['publish_at'].required = False


# articles/forms.py
# articles/forms.py

class GuelekanForm(forms.ModelForm):
    galleries = forms.ModelMultipleChoiceField(
        queryset=Gallery.objects.all(), 
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Galeries associées"
    )
    
    intervenants = forms.ModelMultipleChoiceField(
        queryset=Intervenant.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Intervenants"
    )
    
    class Meta:
        model = Guelekan
        # AJOUTER 'intervenants' dans la liste des champs
        fields = [
            'title', 'subtitle', 'content', 'status', 
            'cover_image', 'pdf_file', 'galleries', 'intervenants', 
            'publish_at'
        ]
        widgets = {
            'publish_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local', 
                'class': 'form-control'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Titre du séminaire'
            }),
            'subtitle': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Sous-titre optionnel'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 10,
                'placeholder': 'Contenu du séminaire...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pré-selectionner les intervenants si l'instance existe
        if self.instance and self.instance.pk:
            self.fields['intervenants'].initial = self.instance.intervenants.all()
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            # Sauvegarder les relations many-to-many
            self.save_m2m()
            # Sauvegarder les intervenants
            instance.intervenants.set(self.cleaned_data['intervenants'])
        return instance