from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from site_web import mailing
from ..filters import MemberFilterForm
from ..listing import paginate
from ..forms import CustomMemberCreationForm, CustomUserCreationForm, CustomUserUpdateForm
from ..permissions import moderator_required
from ..models import CustomUser


@moderator_required
def create_user_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES) 
        if form.is_valid():
            form.save()
            messages.success(request, "Utilisateur créé avec succès!")
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'users/register.html', {'form': form})


@moderator_required
def user_list_view(request):
    form = MemberFilterForm(request.GET)
    members = form.apply(CustomUser.objects.exclude(role='admin').order_by('nom', 'prenom'))
    page_obj, querystring = paginate(request, members)
    return render(request, 'users/user_list.html', {
        'form': form,
        'page_obj': page_obj,
        'querystring': querystring,
        'role_choices': MemberFilterForm.base_fields['role'].choices,
    })


@moderator_required
def user_detail_view(request, id):
    user = get_object_or_404(CustomUser, id=id)
    return render(request, 'users/user_detail.html', {'user_detail': user})


@moderator_required
def create_member_view(request):
    if request.user.role not in ['admin', 'moderateur']:
        return redirect('login')

    if request.method == 'POST':
        form = CustomMemberCreationForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            messages.success(request, "Le membre a été créé avec succès.")
            if member.backoffice_access:
                _notify_access_granted(request, member)
            return redirect('user_list')  # ou admin_dashboard
    else:
        form = CustomMemberCreationForm()
    return render(request, 'users/create_member.html', {'form': form})


def _notify_access_granted(request, member):
    if mailing.send_access_granted(member):
        messages.info(request, f"{member.get_full_name()} a reçu un e-mail pour activer son accès.")
    else:
        messages.warning(request, f"L'e-mail d'accès à {member.get_full_name()} n'a pas pu être envoyé.")


@login_required
def update_user_view(request, pk):
    user_to_update = get_object_or_404(CustomUser, pk=pk)

    # On modifie son propre profil ; seuls les modérateurs modifient celui des autres,
    # et seuls les administrateurs touchent à un compte administrateur.
    is_self = request.user.pk == user_to_update.pk
    if not is_self and (not request.user.can_moderate or (user_to_update.is_admin and not request.user.is_admin)):
        raise PermissionDenied

    if request.method == 'POST':
        had_access = user_to_update.backoffice_access
        form = CustomUserUpdateForm(request.POST, request.FILES, instance=user_to_update, editor=request.user)
        if form.is_valid():
            updated_user = form.save()
            if updated_user.backoffice_access and not had_access and not is_self:
                _notify_access_granted(request, updated_user)
            
            # Message différent selon qui est modifié
            if request.user.pk == user_to_update.pk:
                messages.success(request, "Votre profil a été mis à jour avec succès.")
            else:
                messages.success(request, f"Le profil de {updated_user.get_full_name()} a été mis à jour.")
            
            return redirect('user_list')
    else:
        form = CustomUserUpdateForm(instance=user_to_update, editor=request.user)
    
    context = {
        'form': form,
        'user_to_update': user_to_update,
        'is_self_update': request.user.pk == user_to_update.pk
    }
    return render(request, 'users/update_user.html', context)


@moderator_required
def user_delete(request, id):
    user_to_delete = get_object_or_404(CustomUser, id=id)
    
    # Empêcher l'auto-suppression
    if user_to_delete == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('user_list')
    
    # Empêcher la suppression d'un administrateur par un modérateur
    if request.user.role == 'moderateur' and user_to_delete.role == 'admin':
        messages.error(request, "Vous n'avez pas les permissions pour supprimer un administrateur.")
        return redirect('user_list')
    
    # Validation de la confirmation
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation', '').strip().upper()
        if confirmation != 'SUPPRIMER':
            messages.error(request, "La confirmation est incorrecte. Veuillez taper 'SUPPRIMER' pour confirmer.")
            return render(request, 'users/user_confirm_delete.html', {'user_to_delete': user_to_delete})
        
        username = user_to_delete.get_full_name()
        user_to_delete.delete()
        messages.success(request, f"Le membre {username} a été supprimé avec succès.")
        return redirect('user_list')
    
    context = {
        'user_to_delete': user_to_delete,
    }
    return render(request, 'users/user_confirm_delete.html', context)
