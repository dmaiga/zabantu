from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .. import dashboard_data


@login_required
def dashboard_view(request):
    user = request.user
    return render(request, 'users/dashboard.html', {
        'now': timezone.now(),
        'todo': dashboard_data.todo_items(user),
        'stats': dashboard_data.current_state(user),
        'next_events': dashboard_data.upcoming_events(user),
        'scheduled': dashboard_data.scheduled_items(user),
        'received': dashboard_data.latest_received(user),
        'activity': dashboard_data.recent_activity(user),
    })
