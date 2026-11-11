"""Backoffice des formations (modérateurs) : cours et fichiers, cohortes et inscriptions, participants."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from users.listing import paginate
from users.permissions import moderator_required

from . import mailing
from .forms import CohortForm, CourseFilesForm, CourseFileTitleForm, CourseForm
from .models import Cohort, Course, CourseFile, Enrollment

User = get_user_model()

ACTION_LABELS = {'accept': 'acceptée(s)', 'reject': 'refusée(s)', 'revoke': 'révoquée(s)'}


def _form_page(request, form, title, back_url, intro=''):
    return render(request, 'courses/admin/form.html', {
        'form': form, 'title': title, 'intro': intro, 'back_url': back_url, 'back_label': 'Retour'})


# ----- Cours -----

@moderator_required
def course_list(request):
    courses = (Course.objects.annotate(n_files=Count('files', distinct=True), n_cohorts=Count('cohorts', distinct=True))
               .order_by('title'))
    query = request.GET.get('q', '').strip()
    if query:
        courses = courses.filter(Q(title__icontains=query) | Q(summary__icontains=query))
    page_obj, querystring = paginate(request, courses)
    return render(request, 'courses/admin/course_list.html', {'page_obj': page_obj, 'querystring': querystring, 'query': query})


@moderator_required
def course_create(request):
    form = CourseForm(request.POST or None)
    if form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        course.save()
        messages.success(request, "Cours créé. Ajoutez maintenant ses fichiers.")
        return redirect('course_admin_detail', pk=course.pk)
    return _form_page(request, form, "Nouveau cours", reverse('course_admin_list'),
                      "Les fichiers s'ajoutent ensuite, depuis la fiche du cours.")


@moderator_required
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    form = CourseForm(request.POST or None, instance=course)
    if form.is_valid():
        form.save()
        messages.success(request, "Cours mis à jour.")
        return redirect('course_admin_detail', pk=course.pk)
    return _form_page(request, form, f"Modifier « {course.title} »", reverse('course_admin_detail', args=[pk]))


@moderator_required
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    files_form = CourseFilesForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and files_form.is_valid():
        start = course.files.count()
        for index, upload in enumerate(files_form.cleaned_data['files']):
            CourseFile.objects.create(course=course, file=upload, order=start + index)
        messages.success(request, f"{len(files_form.cleaned_data['files'])} fichier(s) ajouté(s).")
        return redirect('course_admin_detail', pk=pk)
    return render(request, 'courses/admin/course_detail.html', {
        'course': course, 'files_form': files_form, 'cohorts': course.cohorts.all()})


@require_POST
@moderator_required
def course_file_update(request, pk):
    item = get_object_or_404(CourseFile, pk=pk)
    form = CourseFileTitleForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, "Fichier mis à jour.")
    else:
        messages.error(request, "Titre ou ordre invalide.")
    return redirect('course_admin_detail', pk=item.course_id)


@require_POST
@moderator_required
def course_file_delete(request, pk):
    item = get_object_or_404(CourseFile, pk=pk)
    course_id, name = item.course_id, item.display_name
    item.file.delete(save=False)
    item.delete()
    messages.success(request, f"Fichier « {name} » supprimé.")
    return redirect('course_admin_detail', pk=course_id)


@require_POST
@moderator_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    for item in course.files.all():
        item.file.delete(save=False)
    title = course.title
    course.delete()
    messages.success(request, f"Cours « {title} » supprimé avec ses fichiers.")
    return redirect('course_admin_list')


# ----- Cohortes -----

@moderator_required
def cohort_list(request):
    cohorts = Cohort.objects.annotate(
        n_pending=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.PENDING)),
        n_accepted=Count('enrollments', filter=Q(enrollments__status=Enrollment.Status.ACCEPTED)),
        n_courses=Count('courses', distinct=True),
    ).order_by('-opens_on')
    page_obj, querystring = paginate(request, cohorts)
    return render(request, 'courses/admin/cohort_list.html', {'page_obj': page_obj, 'querystring': querystring})


@moderator_required
def cohort_create(request):
    form = CohortForm(request.POST or None)
    if form.is_valid():
        cohort = form.save(commit=False)
        cohort.created_by = request.user
        cohort.save()
        form.save_m2m()
        messages.success(request, "Cohorte créée.")
        return redirect('cohort_admin_detail', pk=cohort.pk)
    return _form_page(request, form, "Nouvelle cohorte", reverse('cohort_admin_list'),
                      "La cohorte apparaît sur la page « Formations » pendant ses dates d'inscription ; les participants "
                      "sont prévenus par e-mail le jour de l'ouverture.")


@moderator_required
def cohort_update(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    form = CohortForm(request.POST or None, instance=cohort)
    if form.is_valid():
        form.save()
        messages.success(request, "Cohorte mise à jour.")
        return redirect('cohort_admin_detail', pk=pk)
    return _form_page(request, form, f"Modifier « {cohort.name} »", reverse('cohort_admin_detail', args=[pk]))


@require_POST
@moderator_required
def cohort_delete(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    if cohort.enrollments.exists():
        messages.error(request, "Cette cohorte a des inscriptions : elle ne peut pas être supprimée. Fermez plutôt ses inscriptions (date de fermeture).")
        return redirect('cohort_admin_detail', pk=pk)
    name = cohort.name
    cohort.delete()
    messages.success(request, f"Cohorte « {name} » supprimée.")
    return redirect('cohort_admin_list')


@moderator_required
def cohort_detail(request, pk):
    cohort = get_object_or_404(Cohort.objects.prefetch_related('courses'), pk=pk)
    enrollments = cohort.enrollments.select_related('user__participant_profile', 'decided_by')
    status_filter = request.GET.get('status', '')
    if status_filter in Enrollment.Status.values:
        enrollments = enrollments.filter(status=status_filter)
    counts = dict(cohort.enrollments.values_list('status').annotate(n=Count('id')))
    page_obj, querystring = paginate(request, enrollments, per_page=50)
    return render(request, 'courses/admin/cohort_detail.html', {
        'cohort': cohort, 'page_obj': page_obj, 'querystring': querystring, 'status_filter': status_filter,
        'total': sum(counts.values()),
        'statuses': [(value, label, counts.get(value, 0)) for value, label in Enrollment.Status.choices],
    })


def _decide(request, enrollments, action):
    """Applique la décision aux inscriptions qui le permettent et prévient chaque participant. Renvoie (faites, e-mails en échec)."""
    done, mail_failures = 0, 0
    for enrollment in enrollments:
        if enrollment.decide(action, request.user):
            done += 1
            if not mailing.send_decision(enrollment):
                mail_failures += 1
    return done, mail_failures


def _report(request, done, skipped, mail_failures, action):
    if done:
        messages.success(request, f"{done} inscription(s) {ACTION_LABELS[action]} ; participant(s) prévenu(s) par e-mail.")
    if skipped:
        messages.warning(request, f"{skipped} inscription(s) ignorée(s) : action impossible pour leur statut.")
    if mail_failures:
        messages.warning(request, f"{mail_failures} e-mail(s) n'ont pas pu être envoyés (décision enregistrée).")
    if not done and not skipped:
        messages.error(request, "Aucune inscription sélectionnée.")


@require_POST
@moderator_required
def enrollment_action(request, pk, action):
    enrollment = get_object_or_404(Enrollment.objects.select_related('user', 'cohort'), pk=pk)
    if action not in ACTION_LABELS:
        raise ValueError(action)
    done, failures = _decide(request, [enrollment], action)
    _report(request, done, 0 if done else 1, failures, action)
    return redirect(request.POST.get('next') or reverse('cohort_admin_detail', args=[enrollment.cohort_id]))


@require_POST
@moderator_required
def enrollment_bulk(request, pk):
    cohort = get_object_or_404(Cohort, pk=pk)
    action = request.POST.get('action')
    if action not in ACTION_LABELS:
        messages.error(request, "Action inconnue.")
        return redirect('cohort_admin_detail', pk=pk)
    selected = list(cohort.enrollments.filter(pk__in=request.POST.getlist('ids')).select_related('user'))
    done, failures = _decide(request, selected, action)
    _report(request, done, len(selected) - done, failures, action)
    return redirect(request.POST.get('next') or reverse('cohort_admin_detail', args=[pk]))


# ----- Participants -----

@moderator_required
def participant_list(request):
    participants = (User.objects.filter(participant_profile__isnull=False).select_related('participant_profile')
                    .annotate(n_enrollments=Count('enrollments')).order_by('-date_joined'))
    query = request.GET.get('q', '').strip()
    if query:
        participants = participants.filter(Q(nom__icontains=query) | Q(prenom__icontains=query) | Q(email__icontains=query)
                                           | Q(participant_profile__organization__icontains=query))
    page_obj, querystring = paginate(request, participants)
    return render(request, 'courses/admin/participant_list.html',
                  {'page_obj': page_obj, 'querystring': querystring, 'query': query})
