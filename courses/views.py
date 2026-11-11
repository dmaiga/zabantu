"""Connexion commune, compte et espace participant (bilingues).

- Une seule page de connexion pour tout le monde (équipe et participants) ; l'aiguillage se fait côté serveur :
  backoffice pour l'équipe, espace participant pour les comptes qui en ont un.
- La création de compte sur le site est réservée aux participants (les comptes de l'équipe se créent au backoffice).
- L'espace participant est une zone à part (barre latérale, sans l'en-tête du site) : tableau de bord, cours,
  formations, profil, mot de passe, demande d'adhésion.
"""
import mimetypes
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Prefetch
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from site_web import antispam
from site_web.models import MembershipApplication

from . import mailing
from .backends import PARTICIPANT_ROLE, has_space
from .forms import EnrollmentForm, MembershipLightForm, ParticipantProfileForm, SignupForm, SiteLoginForm
from .models import Cohort, Course, CourseFile, Enrollment, ParticipantProfile

User = get_user_model()


def home_for(user):
    """Où envoyer un compte après la connexion."""
    if user.can_access_backoffice:
        return reverse('dashboard')
    return reverse('participant_space')


def _safe_next(request, default):
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return default


def _safe_target(request, target):
    """Conserve uniquement une destination locale entre la création et la confirmation du compte."""
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return ''


def _login_url(request):
    return f"{reverse('login')}?{urlencode({'next': request.get_full_path()})}"


def space_required(view):
    """Page de l'espace participant : connexion demandée ; un compte de l'équipe sans espace va au backoffice."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(_login_url(request))
        if not has_space(request.user):
            return redirect('dashboard' if request.user.can_access_backoffice else 'home')
        return view(request, *args, **kwargs)
    return wrapper


def course_access_required(view):
    """Cours et fichiers : participants (accès vérifié par la vue) et modérateurs (aperçu)."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(_login_url(request))
        if not has_space(request.user) and not request.user.can_moderate:
            return redirect('dashboard' if request.user.can_access_backoffice else 'home')
        return view(request, *args, **kwargs)
    return wrapper


def _space(request, template, context=None, active=''):
    """Rendu d'une page de l'espace participant (gabarit à barre latérale)."""
    context = context or {}
    context.setdefault('active', active)
    context['pending_count'] = Enrollment.objects.filter(user=request.user, status=Enrollment.Status.PENDING).count()
    return render(request, template, context)


# ----- Connexion commune -----

def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request, home_for(request.user)))
    form = SiteLoginForm(request, request.POST or None)
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '')
        wait = antispam.login_wait_seconds(identifier)
        if wait:
            messages.error(request, antispam.login_block_message(wait))
        elif form.is_valid():
            antispam.login_succeeded(identifier)
            login(request, form.user)
            return redirect(_safe_next(request, home_for(form.user)))
        else:
            blocked = antispam.login_failed(identifier)
            if blocked:
                messages.error(request, antispam.login_block_message(blocked))
    return render(request, 'courses/public/login.html', {'form': form, 'next': request.GET.get('next', '')})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, _("Vous êtes déconnecté."))
    return redirect('home')


# ----- Création du compte (participants uniquement) -----

def signup(request):
    if request.user.is_authenticated:
        return redirect(home_for(request.user))
    next_url = _safe_target(request, request.POST.get('next') or request.GET.get('next'))
    form = SignupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save(language=request.LANGUAGE_CODE)
            mailing.send_confirmation(user)
            request.session['participant_signup_email'] = user.email
            if next_url:
                request.session['participant_signup_next'] = next_url
            else:
                request.session.pop('participant_signup_next', None)
            return redirect('participant_signup_done')
        if antispam.is_bot_rejection(form):
            antispam.show_antispam_errors(request, form)
    return render(request, 'courses/public/signup.html', {'form': form, 'next': next_url})


def signup_done(request):
    return render(request, 'courses/public/signup_done.html',
                  {'email': request.session.get('participant_signup_email', '')})


def confirm(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)), role=PARTICIPANT_ROLE)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None
    if user is None or not mailing.confirmation_token.check_token(user, token):
        if user is not None and user.is_active:
            messages.info(request, _("Votre adresse est déjà confirmée : connectez-vous."))
            return redirect('login')
        return render(request, 'courses/public/confirm_invalid.html', status=400)
    user.is_active = True
    user.save(update_fields=['is_active'])
    login(request, user, backend='courses.backends.ParticipantBackend')
    messages.success(request, _("Votre compte est confirmé. Bienvenue !"))
    return redirect(request.session.pop('participant_signup_next', None) or 'participant_space')


class PasswordResetView(auth_views.PasswordResetView):
    template_name = 'courses/public/password_reset.html'
    email_template_name = 'courses/emails/password_reset.txt'
    html_email_template_name = 'courses/emails/password_reset.html'
    subject_template_name = 'courses/emails/password_reset_subject.txt'
    success_url = reverse_lazy('participant_password_reset_done')


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'courses/public/password_reset_done.html'


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'courses/public/password_reset_confirm.html'
    success_url = reverse_lazy('participant_password_reset_complete')


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'courses/public/password_reset_complete.html'


# ----- Espace participant -----

def _accepted(user):
    return (Enrollment.objects.filter(user=user, status=Enrollment.Status.ACCEPTED).select_related('cohort')
            .prefetch_related(Prefetch('cohort__courses', queryset=Course.objects.prefetch_related('files'))))


def _open_cohorts_for(user):
    cohorts = list(Cohort.objects.open().prefetch_related('courses').order_by('closes_on'))
    mine = dict(Enrollment.objects.filter(user=user, cohort__in=cohorts).values_list('cohort_id', 'status'))
    for cohort in cohorts:
        cohort.my_status = mine.get(cohort.pk)
    return cohorts


def _membership(user):
    """État de l'adhésion du compte : 'member', 'pending', 'rejected', ou None (aucune demande)."""
    if user.role in ('membre', 'moderateur', 'admin'):
        return 'member'
    application = MembershipApplication.objects.filter(email__iexact=user.email).order_by('-created_at').first()
    if application is None:
        return None
    return {'pending': 'pending', 'approved': 'member'}.get(application.status, 'rejected')


@space_required
def dashboard(request):
    user = request.user
    accepted = list(_accepted(user))
    courses = [course for enrollment in accepted for course in enrollment.cohort.courses.all()]
    open_cohorts = _open_cohorts_for(user)
    return _space(request, 'courses/space/dashboard.html', {
        'accepted': accepted,
        'courses': courses[:6],
        'course_count': len(courses),
        'pending': Enrollment.objects.filter(user=user, status=Enrollment.Status.PENDING).select_related('cohort'),
        'available': [c for c in open_cohorts if not c.my_status],
        'membership': _membership(user),
    }, active='dashboard')


@space_required
def my_courses(request):
    return _space(request, 'courses/space/courses.html', {'accepted': _accepted(request.user)}, active='courses')


@course_access_required
def course_detail(request, pk):
    course = get_object_or_404(Course.objects.prefetch_related('files'), pk=pk)
    if not course.is_accessible_by(request.user):
        raise Http404
    if not has_space(request.user):   # aperçu d'un modérateur
        return render(request, 'courses/space/course_detail.html', {'course': course, 'preview': True})
    return _space(request, 'courses/space/course_detail.html', {'course': course}, active='courses')


@course_access_required
def course_file(request, pk):
    """Téléchargement d'un fichier de cours, après contrôle de l'accès (le fichier n'est jamais public)."""
    item = get_object_or_404(CourseFile.objects.select_related('course'), pk=pk)
    if not item.course.is_accessible_by(request.user):
        raise Http404
    try:
        handle = item.file.open('rb')
    except FileNotFoundError:
        raise Http404
    content_type = mimetypes.guess_type(item.filename)[0] or 'application/octet-stream'
    response = FileResponse(handle, as_attachment=True, filename=item.filename, content_type=content_type)
    response['X-Robots-Tag'] = 'noindex'
    response['Cache-Control'] = 'private, no-store'
    return response


@space_required
def my_trainings(request):
    enrollments = Enrollment.objects.filter(user=request.user).select_related('cohort')
    return _space(request, 'courses/space/trainings.html', {
        'open_cohorts': _open_cohorts_for(request.user), 'enrollments': enrollments}, active='trainings')


def enroll(request, pk):
    cohort = get_object_or_404(Cohort.objects.open().prefetch_related('courses'), pk=pk)
    if not request.user.is_authenticated:
        messages.info(request, _("Connectez-vous ou créez un compte gratuit pour vous inscrire."))
        return redirect(_login_url(request))
    if not has_space(request.user):
        messages.info(request, _("Les inscriptions aux formations se font avec un compte participant."))
        return redirect('training_list')
    if Enrollment.objects.filter(cohort=cohort, user=request.user).exists():
        messages.info(request, _("Vous êtes déjà inscrit(e) à cette formation : suivez votre demande dans « Mes formations »."))
        return redirect('participant_trainings')
    form = EnrollmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        enrollment = form.save(commit=False)
        enrollment.cohort, enrollment.user = cohort, request.user
        enrollment.save()
        ParticipantProfile.objects.filter(user=request.user).update(language=request.LANGUAGE_CODE)
        messages.success(request, _("Votre demande est envoyée. Vous recevrez la réponse de l'équipe par e-mail."))
        return redirect('participant_trainings')
    return _space(request, 'courses/space/enroll.html', {'cohort': cohort, 'form': form}, active='trainings')


@space_required
def profile(request):
    form = ParticipantProfileForm(request.POST or None, instance=request.user.participant_profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Votre profil est enregistré."))
        return redirect('participant_profile')
    return _space(request, 'courses/space/profile.html', {'form': form}, active='profile')


@space_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)   # la session reste ouverte avec le nouveau mot de passe
        messages.success(request, _("Votre mot de passe est modifié."))
        return redirect('participant_profile')
    return _space(request, 'courses/space/password.html', {'form': form}, active='password')


@space_required
def membership(request):
    state = _membership(request.user)
    form = None
    if state is None:
        form = MembershipLightForm(request.POST or None,
                                   initial={'institution': request.user.participant_profile.organization})
        if request.method == 'POST' and form.is_valid():
            from site_web import mailing as site_mailing
            application = form.save(request.user, request.LANGUAGE_CODE)
            site_mailing.send_application_received(application)
            messages.success(request, _("Votre demande d'adhésion est envoyée. L'équipe vous répondra par e-mail."))
            return redirect('participant_membership')
    return _space(request, 'courses/space/membership.html', {'state': state, 'form': form}, active='membership')


# ----- Page publique « Formations » -----

def training_list(request):
    cohorts = Cohort.objects.open().prefetch_related('courses').order_by('closes_on')
    mine = {}
    if request.user.is_authenticated:
        mine = dict(Enrollment.objects.filter(user=request.user, cohort__in=cohorts).values_list('cohort_id', 'status'))
    for cohort in cohorts:
        cohort.my_status = mine.get(cohort.pk)
    return render(request, 'courses/public/training_list.html', {'cohorts': cohorts})
