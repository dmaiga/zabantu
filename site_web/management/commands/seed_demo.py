"""Peuple la base avec des données de démonstration pour visualiser le site public.

Usage :
    python manage.py seed_demo           # ajoute les données (idempotent)
    python manage.py seed_demo --reset   # supprime d'abord les données de démo

Les objets créés sont repérables : membres @demo.zabantu.org, slugs préfixés « demo- »,
partenaires/photos/galeries dont le titre figure dans les listes ci-dessous.
"""
import io
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from articles.models import Article, Guelekan
from events.models import Event, EventIntervenant
from gallery.models import Gallery, Photo, PhotoTag
from intervenants.models import Intervenant
from users.models import Partenaire

User = get_user_model()

DEMO_DOMAIN = 'demo.zabantu.org'
PALETTE = [
    (31, 78, 121), (46, 125, 90), (176, 96, 38), (122, 58, 120),
    (150, 52, 52), (44, 100, 140), (90, 110, 40), (60, 60, 90),
]

MEMBRES = [
    ('Awa', 'Diallo', 'Politiques publiques', 'Chercheuse associée', 'Gouvernance, décentralisation et services publics au Sahel.'),
    ('Moussa', 'Traoré', 'Économie', 'Économiste senior', 'Économie du développement et finances publiques en Afrique de l\'Ouest.'),
    ('Fatoumata', 'Keita', 'Sociologie', 'Docteure en sociologie', 'Dynamiques sociales, jeunesse et migrations.'),
    ('Ibrahim', 'Coulibaly', 'Sécurité', 'Analyste sécurité', 'Gouvernance de la sécurité et transitions politiques.'),
    ('Mariam', 'Sangaré', 'Droit', 'Juriste', 'Droit constitutionnel et institutions régionales.'),
    ('Seydou', 'Bagayoko', 'Environnement', 'Chargé de recherche', 'Changement climatique, agriculture et sécurité alimentaire.'),
]

INTERVENANTS = [
    ('Aminata', 'Cissé', 'Université de Bamako', 'Professeure', 'expert'),
    ('Oumar', 'Sow', 'CODESRIA', 'Directeur de programme', 'speaker'),
    ('Nadia', 'Benali', 'Université Mohammed V', 'Chercheuse', 'panelist'),
    ('Kwame', 'Mensah', 'University of Ghana', 'Senior Lecturer', 'speaker'),
    ('Hawa', 'Konaté', 'Fondation pour la paix', 'Modératrice', 'moderator'),
]

PARTENAIRES = [
    'Fondation Horizon', 'Université de Bamako', 'CODESRIA', 'Institut Sahel',
    'Open Society Initiative', 'Réseau Afrique Recherche',
]

# (titre, type, sous-titre, résumé)
ARTICLES = [
    ('Décentralisation et services de base au Mali', 'zabantu', 'Bilan de vingt ans de réformes', 'Cette étude examine l\'effet de la décentralisation sur l\'accès aux services de base.'),
    ('Jeunesse et emploi dans le Sahel central', 'analyse', 'Perspectives et obstacles', 'Une analyse des trajectoires d\'insertion professionnelle des jeunes urbains.'),
    ('Sécurité alimentaire et changement climatique', 'policy', 'Recommandations pour les décideurs', 'Note de politique publique sur l\'adaptation des systèmes agricoles.'),
    ('Les institutions régionales à l\'épreuve des transitions', 'article', 'CEDEAO et AES : un nouvel équilibre', 'Réflexion sur la recomposition du paysage institutionnel ouest-africain.'),
    ('Migrations et économies locales', 'rapport', 'Rapport annuel 2025', 'Rapport de synthèse sur les transferts et les dynamiques migratoires.'),
    ('Penser l\'État en Afrique de l\'Ouest', 'ouvrage', 'Essai collectif', 'Ouvrage collectif sur les trajectoires de construction de l\'État.'),
    ('Fiscalité locale et développement', 'working', 'Document de travail n° 7', 'Document de travail sur la mobilisation des ressources locales.'),
    ('Gouvernance minière : le cas du Sahel', 'academic', 'Revue africaine de science politique', 'Article académique sur la gouvernance des ressources extractives.'),
    ('Médias et espace public numérique', 'independent', 'Tribune externe', 'Un regard extérieur sur les mutations de l\'espace public.'),
    ('Éducation et langues nationales', 'zabantu', 'Enjeux et expériences', 'Les langues nationales dans l\'enseignement : état des lieux.'),
    ('Financement de la recherche en Afrique', 'analyse', 'Quels modèles durables ?', 'Panorama des mécanismes de financement de la recherche africaine.'),
    ('Villes intermédiaires et croissance', 'article', 'Urbanisation hors capitale', 'Dynamiques économiques des villes intermédiaires maliennes.'),
]

LOREM = [
    'Ce texte de démonstration illustre la mise en page d\'une publication Zabantu. Il permet de vérifier la lisibilité, les marges et la hiérarchie typographique.',
    'La recherche en sciences sociales en Afrique de l\'Ouest fait face à des défis structurels, mais aussi à des opportunités nouvelles portées par une génération de chercheurs engagés.',
    'Les données présentées ici sont fictives. Elles servent uniquement à visualiser le rendu du site avant la mise en ligne de contenus réels.',
]

# (titre, type, jours par rapport à aujourd'hui, durée en heures, lieu, en ligne, à la une)
EVENEMENTS = [
    ('Conférence annuelle Zabantu 2026', 'conference', 21, 8, 'Bamako, Palais de la Culture', False, True),
    ('Atelier : écrire une note de politique publique', 'atelier', 9, 4, 'Bamako, siège Zabantu', False, False),
    ('Webinaire : économie du Sahel après 2025', 'webinaire', 14, 2, 'En ligne', True, False),
    ('Formation à la méthodologie qualitative', 'formation', 35, 16, 'Ségou', False, False),
    ('Séminaire Gɛlɛkan : jeunesse et citoyenneté', 'seminaire', 5, 3, 'Bamako, Maison de la Presse', False, False),
    ('Conférence : fiscalité locale', 'conference', -30, 6, 'Bamako', False, False),
    ('Séminaire Gɛlɛkan : sécurité et gouvernance', 'seminaire', -75, 3, 'Bamako', False, False),
    ('Webinaire : migrations en Afrique de l\'Ouest', 'webinaire', -120, 2, 'En ligne', True, False),
]

GUELEKAN = [
    'Jeunesse et citoyenneté : quelles voies de participation ?',
    'Sécurité et gouvernance dans les régions du Nord',
    'Économie informelle et protection sociale',
    'Femmes, terre et pouvoir de décision',
]

GALERIES = [
    ('Conférence annuelle 2025', True, 8),
    ('Séminaires Gɛlɛkan', True, 6),
    ('Ateliers de formation', False, 6),
    ('Vie de l\'association', False, 4),
]
TAGS = ['Conférence', 'Atelier', 'Portrait', 'Terrain']


def _font(size):
    for path in ('/System/Library/Fonts/Helvetica.ttc', '/Library/Fonts/Arial.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_image(text, size=(1200, 800), seed=0):
    """Image dégradée avec un libellé, enregistrée en JPEG."""
    rng = random.Random(seed)
    c1, c2 = rng.sample(PALETTE, 2)
    w, h = size
    img = Image.new('RGB', size, c1)
    px = img.load()
    for y in range(h):
        t = y / h
        row = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    draw = ImageDraw.Draw(img)
    for _ in range(5):
        r = rng.randint(h // 8, h // 3)
        cx, cy = rng.randint(0, w), rng.randint(0, h)
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255), width=3)
    font = _font(max(24, w // 22))
    words, lines, line = text.split(), [], ''
    for word in words:
        trial = f'{line} {word}'.strip()
        if draw.textlength(trial, font=font) > w * 0.8 and line:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    y = (h - len(lines) * font.size * 1.3) / 2
    for ln in lines:
        draw.text(((w - draw.textlength(ln, font=font)) / 2, y), ln, fill='white', font=font)
        y += font.size * 1.3
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=82)
    return ContentFile(buf.getvalue())


def make_logo(name, seed):
    """Logo partenaire : initiales sur fond blanc."""
    rng = random.Random(seed)
    color = rng.choice(PALETTE)
    img = Image.new('RGB', (480, 240), 'white')
    draw = ImageDraw.Draw(img)
    initials = ''.join(w[0] for w in name.split() if w[0].isalpha())[:3].upper()
    draw.ellipse((40, 40, 200, 200), fill=color)
    big = _font(64)
    draw.text((120 - draw.textlength(initials, font=big) / 2, 78), initials, fill='white', font=big)
    small = _font(28)
    words = name.split()
    mid = (len(words) + 1) // 2
    for i, ln in enumerate((' '.join(words[:mid]), ' '.join(words[mid:]))):
        draw.text((225, 85 + i * 38), ln, fill=color, font=small)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return ContentFile(buf.getvalue())


def make_portrait(initials, seed):
    img = make_image(initials, size=(400, 400), seed=seed)
    return img


class Command(BaseCommand):
    help = "Crée des données de démonstration (membres, publications, événements, galeries, partenaires)."

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help="Supprime d'abord les données de démonstration existantes.")
        parser.add_argument('--force', action='store_true',
                            help="Autorise l'ajout de données fictives dans une base qui contient déjà du vrai contenu.")

    @transaction.atomic
    def handle(self, *args, **options):
        real_content = Article.objects.exclude(slug__startswith='demo-').count() + Event.objects.exclude(
            slug__startswith='demo-').count()
        if real_content and not options['force']:
            raise CommandError(
                f"Cette base contient déjà du vrai contenu ({real_content} publication(s) ou événement(s)) : "
                "les données fictives s'y mélangeraient. Utilisez une base vide, ou --force si c'est voulu.")
        if options['reset']:
            self.reset()
        self.stdout.write('Création des données de démonstration…')
        members = self.seed_members()
        intervenants = self.seed_intervenants()
        self.seed_partenaires()
        self.seed_articles(members)
        self.seed_events(members, intervenants)
        galleries = self.seed_galleries(members)
        self.seed_guelekan(intervenants, galleries)
        self.stdout.write(self.style.SUCCESS(
            'Terminé. Lancez « python manage.py runserver » et ouvrez http://127.0.0.1:8000/'))

    # ------------------------------------------------------------------ reset
    def reset(self):
        Article.objects.filter(slug__startswith='demo-').delete()
        Guelekan.objects.filter(slug__startswith='demo-').delete()
        Event.objects.filter(slug__startswith='demo-').delete()
        Gallery.objects.filter(slug__startswith='demo-').delete()
        Photo.objects.filter(title__startswith='[démo]').delete()
        PhotoTag.objects.filter(slug__startswith='demo-').delete()
        Intervenant.objects.filter(email__endswith='@' + DEMO_DOMAIN).delete()
        Partenaire.objects.filter(name__in=PARTENAIRES).delete()
        User.objects.filter(email__endswith='@' + DEMO_DOMAIN).delete()
        self.stdout.write('Données de démonstration supprimées.')

    # ---------------------------------------------------------------- membres
    def seed_members(self):
        members = []
        for i, (prenom, nom, dept, poste, bio) in enumerate(MEMBRES):
            email = f'{prenom.lower()}.{nom.lower()}@{DEMO_DOMAIN}'
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': f'demo-{prenom.lower()}-{nom.lower()}',
                    'prenom': prenom, 'nom': nom, 'role': 'membre',
                    'department': dept, 'job_title': poste, 'bio': bio,
                    'social_linkedin': 'https://www.linkedin.com/',
                    'scholar_link': 'https://scholar.google.com/',
                },
            )
            if created:
                user.set_password('demo12345')
                user.profile_picture.save(f'demo_{i}.jpg', make_portrait(prenom[0] + nom[0], i), save=False)
                user.save()
            members.append(user)
        self.stdout.write(f'  {len(members)} membres (mot de passe : demo12345)')
        return members

    def seed_intervenants(self):
        result = []
        for i, (prenom, nom, org, poste, kind) in enumerate(INTERVENANTS):
            email = f'{prenom.lower()}.{nom.lower()}@{DEMO_DOMAIN}'
            obj, created = Intervenant.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': prenom, 'last_name': nom, 'organization': org,
                    'position': poste, 'intervenant_type': kind,
                    'bio': f'{prenom} {nom} intervient régulièrement sur les questions de développement et de gouvernance.',
                    'expertise': 'Gouvernance, développement, politiques publiques',
                },
            )
            if created:
                obj.photo.save(f'demo_int_{i}.jpg', make_portrait(prenom[0] + nom[0], 50 + i), save=True)
            result.append(obj)
        self.stdout.write(f'  {len(result)} intervenants')
        return result

    def seed_partenaires(self):
        for i, name in enumerate(PARTENAIRES):
            obj, created = Partenaire.objects.get_or_create(name=name, defaults={'order': i, 'is_active': True})
            if created:
                obj.logo.save(f'demo_partenaire_{i}.png', make_logo(name, i), save=True)
        self.stdout.write(f'  {len(PARTENAIRES)} partenaires')

    # ----------------------------------------------------------- publications
    def seed_articles(self, members):
        now = timezone.now()
        body = ''.join(f'<p>{p}</p>' for p in LOREM * 2)
        for i, (title, kind, subtitle, resume) in enumerate(ARTICLES):
            slug = f'demo-{i + 1}'
            if Article.objects.filter(slug=slug).exists():
                continue
            art = Article(
                slug=slug, title=title, article_type=kind, subtitle=subtitle,
                status='published', publish_at=now - timedelta(days=7 * i + 2),
                content=body, resume=resume, abstract=resume,
            )
            if kind == 'academic':
                art.academic_authors = 'Dr. A. Konaté, Pr. B. Ouattara'
                art.journal = 'Revue africaine de science politique'
                art.publication_year = 2025
                art.publisher = 'Éditions du Sahel'
            elif kind == 'independent':
                art.external_author = 'Collectif de recherche indépendant'
                art.external_link = 'https://example.org/article'
            elif kind == 'working':
                art.institution = 'Zabantu'
                art.working_number = str(7 + i)
                art.working_series = 'Documents de travail Zabantu'
                art.working_year = 2025
            art.cover_image.save(f'demo_article_{i}.jpg', make_image(title, seed=100 + i), save=False)
            art.save()
            art.authors.set(random.Random(i).sample(members, k=min(2, len(members))))
            # `publish_at` est forcé à « maintenant » par save() seulement s'il est vide
        # un brouillon, invisible côté public
        if not Article.objects.filter(slug='demo-brouillon').exists():
            art = Article.objects.create(slug='demo-brouillon', title='Brouillon (non visible)',
                                         article_type='zabantu', status='draft', content=body)
            art.authors.set(members[:1])
        self.stdout.write(f'  {len(ARTICLES)} publications')

    # -------------------------------------------------------------- événements
    def seed_events(self, members, intervenants):
        now = timezone.now()
        for i, (title, kind, offset, hours, place, online, featured) in enumerate(EVENEMENTS):
            slug = f'demo-event-{i + 1}'
            if Event.objects.filter(slug=slug).exists():
                continue
            start = (now + timedelta(days=offset)).replace(hour=9, minute=0, second=0, microsecond=0)
            ev = Event(
                slug=slug, title=title, event_type=kind, status='published',
                content='\n\n'.join(LOREM), date=start, end_date=start + timedelta(hours=hours),
                location=place, is_webinar=online, is_featured=featured,
                webinar_link='https://meet.example.org/zabantu' if online else None,
                author=members[0], target_audience='Chercheurs, étudiants, décideurs',
                expected_attendees=80, primary_topic='Gouvernance', secondary_topics='Développement, Sahel',
            )
            ev.image.save(f'demo_event_{i}.jpg', make_image(title, seed=200 + i), save=False)
            ev.save()
            for order, intervenant in enumerate(random.Random(i).sample(intervenants, k=3)):
                EventIntervenant.objects.create(
                    event=ev, intervenant=intervenant, order=order,
                    role=intervenant.intervenant_type if order else 'moderator',
                )
        self.stdout.write(f'  {len(EVENEMENTS)} événements (à venir et passés)')

    # ---------------------------------------------------------------- galeries
    def seed_galleries(self, members):
        tags = []
        for name in TAGS:
            tag, _ = PhotoTag.objects.get_or_create(slug=f'demo-{name.lower()}', defaults={'name': name})
            tags.append(tag)
        galleries = []
        for i, (title, featured, count) in enumerate(GALERIES):
            gallery, created = Gallery.objects.get_or_create(
                slug=f'demo-galerie-{i + 1}',
                defaults={'title': title, 'description': LOREM[0], 'is_featured': featured,
                          'created_by': members[0]},
            )
            galleries.append(gallery)
            if not created:
                continue
            gallery.cover_image.save(f'demo_gal_{i}.jpg', make_image(title, seed=300 + i), save=True)
            for j in range(count):
                photo = Photo(gallery=gallery, title=f'[démo] {title} {j + 1}', uploaded_by=members[0])
                photo.image.save(f'demo_photo_{i}_{j}.jpg',
                                 make_image(f'{title} {j + 1}', size=(1200, 800 if j % 3 else 900),
                                            seed=400 + i * 20 + j), save=True)
                photo.tags.add(tags[(i + j) % len(tags)])
        self.stdout.write(f'  {len(GALERIES)} galeries avec photos')
        return galleries

    # --------------------------------------------------------------- Guelekan
    def seed_guelekan(self, intervenants, galleries):
        body = ''.join(f'<p>{p}</p>' for p in LOREM * 2)
        for i, title in enumerate(GUELEKAN):
            slug = f'demo-guelekan-{i + 1}'
            if Guelekan.objects.filter(slug=slug).exists():
                continue
            obj = Guelekan(title=title, subtitle='Séminaire de discussion ouvert au public',
                           content=body, status='published',
                           publish_at=timezone.now() - timedelta(days=30 * (i + 1)))
            obj.slug = slug
            obj.cover_image.save(f'demo_guelekan_{i}.jpg', make_image(title, seed=500 + i), save=False)
            obj.save()
            obj.intervenants.set(random.Random(i).sample(intervenants, k=2))
            obj.galleries.set(galleries[1:2])
        self.stdout.write(f'  {len(GUELEKAN)} séminaires Gɛlɛkan')
