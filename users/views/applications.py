from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from site_web import mailing
from site_web.models import MembershipApplication
from ..permissions import moderator_required


@moderator_required
def membership_application_list(request):
    Status = MembershipApplication.Status
    applications = MembershipApplication.objects.all()

    status_filter = request.GET.get('status', '')
    if status_filter in Status.values:
        applications = applications.filter(status=status_filter)

    query = request.GET.get('q', '').strip()
    if query:
        applications = applications.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query) | Q(institution__icontains=query)
        )

    page_obj = Paginator(applications, 20).get_page(request.GET.get('page'))
    counts = {s: MembershipApplication.objects.filter(status=s).count() for s in Status.values}
    return render(request, 'users/membership_application_list.html', {
        'applications': page_obj,
        'status_filter': status_filter,
        'query': query,
        'counts': counts,
        'total_count': sum(counts.values()),
    })


@moderator_required
def membership_application_detail(request, pk):
    application = get_object_or_404(MembershipApplication, pk=pk)
    return render(request, 'users/membership_application_detail.html', {'application': application})


@require_POST
@moderator_required
def membership_application_action(request, pk, action):
    application = get_object_or_404(MembershipApplication, pk=pk)
    Status = MembershipApplication.Status
    name = application.full_name

    if action == 'approve' and application.status in (Status.PENDING, Status.REJECTED, Status.REVOKED):
        application.approve(request.user)
        if mailing.send_application_approved(application):
            messages.success(request, f"L'adhésion de {name} a été validée et un e-mail de bienvenue lui a été envoyé.")
        else:
            messages.warning(request, f"L'adhésion de {name} a été validée, mais l'e-mail de bienvenue n'a pas pu être envoyé.")
    elif action == 'reject' and application.status == Status.PENDING:
        application.reject(request.user)
        messages.success(request, f"La demande de {name} a été refusée.")
    elif action == 'revoke' and application.status == Status.APPROVED:
        application.revoke(request.user, request.POST.get('reason', '').strip())
        messages.success(request, f"L'adhésion de {name} a été révoquée.")
    elif action == 'reset' and application.status != Status.PENDING:
        application.reset_to_pending()
        messages.success(request, f"La demande de {name} est de nouveau en attente.")
    else:
        messages.error(request, "Action impossible pour le statut actuel de cette demande.")
    return redirect('membership_application_detail', pk=pk)
