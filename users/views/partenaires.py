from django.contrib import messages
from django.db.models import Q
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..forms import PartenaireForm
from ..listing import paginate
from ..models import Partenaire
from ..permissions import moderator_required


@moderator_required
def partenaire_list(request):
    query = request.GET.get('q', '').strip()
    partenaires = Partenaire.objects.all()
    if query:
        partenaires = partenaires.filter(Q(name__icontains=query))
    page_obj, querystring = paginate(request, partenaires)
    return render(request, "users/partenaires/list.html", {
        "page_obj": page_obj,
        "querystring": querystring,
        "query": query,
    })


@moderator_required
def partenaire_create(request):
    form = PartenaireForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Partenaire créé avec succès.")
        return redirect("partenaire_list")
    return render(request, "users/partenaires/form.html", {"form": form, "title": "Nouveau partenaire",
        "back_url": reverse("partenaire_list")})


@moderator_required
def partenaire_update(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    form = PartenaireForm(request.POST or None, request.FILES or None, instance=partenaire)
    if form.is_valid():
        form.save()
        messages.success(request, "Partenaire mis à jour.")
        return redirect("partenaire_list")
    return render(request, "users/partenaires/form.html", {
        "form": form, "title": f"Modifier {partenaire.name}", "partenaire": partenaire,
        "back_url": reverse("partenaire_list")})


@moderator_required
def partenaire_detail(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    return render(request, "users/partenaires/detail.html", {"partenaire": partenaire})


@require_POST
@moderator_required
def partenaire_toggle(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    partenaire.is_active = not partenaire.is_active
    partenaire.save()
    messages.success(request, f"Partenaire {'activé' if partenaire.is_active else 'désactivé'}.")
    return redirect("partenaire_list")


@require_POST
@moderator_required
def partenaire_delete(request, pk):
    partenaire = get_object_or_404(Partenaire, pk=pk)
    name = partenaire.name
    partenaire.delete()
    messages.success(request, f"Partenaire « {name} » supprimé.")
    return redirect("partenaire_list")
