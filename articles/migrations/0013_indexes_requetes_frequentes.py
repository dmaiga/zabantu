# Index des listes publiques : statut, puis date de publication décroissante, dates vides en dernier
# (même ordre que PUBLICATION_ORDER dans site_web/views.py). Aucune donnée modifiée.
#
# SQLite (tests) refuse « NULLS LAST » dans un index : il y reçoit le même index sans cette précision.
# L'état des modèles est le même partout.

from django.db import migrations, models

INDEXES = {
    'article': 'article_status_publish_idx',
    'guelekan': 'guelekan_status_publish_idx',
}


def _index(name, exact):
    if exact:
        return models.Index(models.F('status'), models.OrderBy(models.F('publish_at'), descending=True, nulls_last=True), name=name)
    return models.Index(fields=['status', '-publish_at'], name=name)


def add_indexes(apps, schema_editor):
    exact = schema_editor.connection.features.supports_expression_indexes and schema_editor.connection.vendor != 'sqlite'
    for model_name, name in INDEXES.items():
        schema_editor.add_index(apps.get_model('articles', model_name), _index(name, exact))


def remove_indexes(apps, schema_editor):
    for model_name, name in INDEXES.items():
        schema_editor.remove_index(apps.get_model('articles', model_name), _index(name, False))


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0012_alter_article_cover_image_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[migrations.RunPython(add_indexes, remove_indexes)],
            state_operations=[
                migrations.AddIndex(model_name=model_name, index=_index(name, True))
                for model_name, name in INDEXES.items()
            ],
        ),
    ]
