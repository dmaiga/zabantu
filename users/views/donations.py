"""Numéros affichés sur la page de don du site (/soutenir/)."""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from site_web.models import DonationNumber

from ..forms import DonationNumberForm
from ..listing import paginate
from ..permissions import moderator_required

__all__ = ['donation_number_list', 'donation_number_create', 'donation_number_update',
           'donation_number_toggle', 'donation_number_delete']


@moderator_required
def donation_number_list(request):
    page_obj, querystring = paginate(request, DonationNumber.objects.all())
    return render(request, 'users/donations/list.html', {'page_obj': page_obj, 'querystring': querystring})


def _form_page(request, form, title):
    return render(request, 'users/donations/form.html', {
        'form': form, 'title': title, 'back_url': reverse('donation_number_list')})


@moderator_required
def donation_number_create(request):
    form = DonationNumberForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Numéro ajouté.")
        return redirect('donation_number_list')
    return _form_page(request, form, "Nouveau numéro de don")


@moderator_required
def donation_number_update(request, pk):
    number = get_object_or_404(DonationNumber, pk=pk)
    form = DonationNumberForm(request.POST or None, instance=number)
    if form.is_valid():
        form.save()
        messages.success(request, "Numéro mis à jour.")
        return redirect('donation_number_list')
    return _form_page(request, form, f"Modifier {number.number}")


@require_POST
@moderator_required
def donation_number_toggle(request, pk):
    number = get_object_or_404(DonationNumber, pk=pk)
    number.is_active = not number.is_active
    number.save()
    messages.success(request, f"Numéro {'affiché sur le site' if number.is_active else 'masqué'}.")
    return redirect('donation_number_list')


@require_POST
@moderator_required
def donation_number_delete(request, pk):
    number = get_object_or_404(DonationNumber, pk=pk)
    label = number.number
    number.delete()
    messages.success(request, f"Numéro « {label} » supprimé.")
    return redirect('donation_number_list')
