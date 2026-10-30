
from django.contrib import admin
from .models import Article,Guelekan
from django.contrib import admin

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'list_authors', 'status', 'created_at']
    search_fields = ['title', 'authors__username']
    list_filter = ['status', 'created_at']

    def list_authors(self, obj):
        return ", ".join([author.get_full_name() or author.username for author in obj.authors.all()])
    list_authors.short_description = "Auteurs"

@admin.register(Guelekan)
class GuelekanAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'created_at', 'publish_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'subtitle', 'content']
    
    # Permet la sélection multiple plus pratique pour ManyToMany
    filter_horizontal = ['galleries', 'intervenants'] 
    
    # Masquer complètement les champs meta et slug de l'interface admin
    exclude = ['meta_title', 'meta_description', 'slug']
    
    # Champs à afficher dans l'admin
    fieldsets = (
        ('Contenu principal', {
            'fields': ('title', 'subtitle', 'content', 'status')
        }),
        ('Intervenants', {
            'fields': ('intervenants',),
            'description': 'Sélectionnez les intervenants liés au séminaire'
        }),
        ('Médias', {
            'fields': ('cover_image', 'pdf_file', 'galleries')
        }),
        ('Publication', {
            'fields': ('publish_at',),
            'classes': ('collapse',),
            'description': 'Optionnel: planifiez la publication'
        })
    )
