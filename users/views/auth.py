from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import DetailView, UpdateView
from ..forms import CustomPasswordChangeForm, LoginForm, ProfileEditForm
from ..models import CustomUser


class ProfileView(LoginRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'users/profile.html'
    context_object_name = 'user'

    def get_object(self):
        return self.request.user


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = ProfileEditForm
    template_name = 'users/profile_edit.html'
    success_url = reverse_lazy('profile')

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        return super().get_context_data(back_url=reverse_lazy('profile'), back_label='Mon profil', **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Votre profil a été mis à jour avec succès.")
        return super().form_valid(form)


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'users/password_change.html'
    success_url = reverse_lazy('profile')

    def form_valid(self, form):
        messages.success(self.request, "Votre mot de passe a été changé avec succès.")
        return super().form_valid(form)


def _valid_credentials_without_access(username, password):
    """Vrai si l'identifiant et le mot de passe sont corrects mais que le compte n'a pas l'accès."""
    candidate = CustomUser.objects.filter(is_active=True).filter(
        Q(username__iexact=username) | Q(email__iexact=username)).first()
    return bool(candidate and candidate.check_password(password) and not candidate.can_access_backoffice)


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Bienvenue {user.get_full_name()} !")
                
                # Redirection vers la page demandée (si elle appartient à ce site) ou dashboard
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url and url_has_allowed_host_and_scheme(
                        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(next_url)
                return redirect('dashboard')
            elif _valid_credentials_without_access(username, password):
                messages.error(request, "Votre compte n'a pas accès à l'espace de gestion.")
            else:
                messages.error(request, "Identifiants invalides")
        else:
            messages.error(request, "Veuillez corriger les erreurs ci-dessous")
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('login')
