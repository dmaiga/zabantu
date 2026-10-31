# articles/forms.py
from django import forms
from django_summernote.widgets import SummernoteWidget, SummernoteInplaceWidget
from users.formsupport import SectionedFormMixin
from .models import Article
from users.models import CustomUser
from users.models import CustomUser
from intervenants.models import Intervenant
from .models import Guelekan
from gallery.models import  Gallery


#09_08
class BaseArticleForm(SectionedFormMixin, forms.ModelForm):
    sections = (
        ('Contenu', ('title', 'subtitle', 'resume', 'abstract', 'content')),
        ('Auteurs', ('authors', 'academic_authors', 'external_author')),
        ('Références', ('journal', 'publisher', 'publication_year', 'institution', 'working_series',
                        'working_number', 'working_year', 'external_link', 'external_link_academique',
                        'publisher_book', 'publication_place', 'page_count', 'publication_date')),
        ('Image et fichier', ('cover_image', 'independent_cover', 'pdf_file')),
    )

    # Champs obligatoires de chaque type de publication : déclarés ici pour que l'astérisque, l'attribut HTML
    # « required » et le message d'erreur soient cohérents (au lieu de règles cachées dans clean()).
    required_fields = ()
    at_least_one_author = False

    class Meta:
        model = Article
        fields = ['title', 'cover_image', 'pdf_file']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.required_fields:
            if name in self.fields:
                self.fields[name].required = True
        if 'authors' in self.fields:
            self.fields['authors'].queryset = CustomUser.objects.exclude(role='admin')
        if self.at_least_one_author:
            # La règle est « l'un ou l'autre » : le champ des membres ne doit pas être obligatoire à lui seul
            if 'authors' in self.fields:
                self.fields['authors'].required = False
            hint = "Au moins un auteur est requis : membre Zabantu ou auteur externe."
            for name in ('authors', 'academic_authors'):
                if name in self.fields:
                    self.fields[name].help_text = hint

    def clean(self):
        cleaned = super().clean()
        if self.at_least_one_author and not cleaned.get('authors') and not cleaned.get('academic_authors'):
            raise forms.ValidationError("Renseignez au moins un auteur (membre Zabantu ou auteur externe).")
        return cleaned


class ArticleForm(BaseArticleForm):
    required_fields = ('authors',)
    content = forms.CharField(widget=SummernoteWidget(), required=True)

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'subtitle',
            'authors',
            'external_author',
            'content',
        ]


class AcademicForm(BaseArticleForm):
    required_fields = ('publication_year', 'journal')
    at_least_one_author = True
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
        labels = {'external_link_academique': "Lien vers l'article"}


class OuvrageForm(BaseArticleForm):
    required_fields = ('publisher_book', 'publication_date')
    at_least_one_author = True
    resume = forms.CharField(widget=SummernoteWidget(), required=False, label='Résumé')
    publication_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'), label='Date de publication')

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'subtitle',
            'authors',
            'academic_authors',
            'publisher_book',
            'publication_place',
            'page_count',
            'publication_date',
            'resume',
        ]


class IndependentForm(BaseArticleForm):
    required_fields = ('external_author', 'external_link')
    resume = forms.CharField(widget=SummernoteWidget(), required=True)

    class Meta(BaseArticleForm.Meta):
        fields = BaseArticleForm.Meta.fields + [
            'external_author',
            'external_link',
            'resume', 
        ]


class WorkingPaperForm(BaseArticleForm):
    required_fields = ('institution', 'working_number', 'working_year')
    at_least_one_author = True
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


#________________________________________________________________
# articles/forms.py


class GuelekanForm(SectionedFormMixin, forms.ModelForm):
    sections = (
        ('Séminaire', ('title', 'subtitle', 'content', 'cover_image', 'pdf_file')),
        ('Invités et galeries', ('intervenants', 'galleries')),
        ('Publication', ('status', 'publish_at')),
    )
    content = forms.CharField(widget=SummernoteWidget(), required=True, label='Contenu')
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