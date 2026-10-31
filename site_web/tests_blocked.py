from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.test import TestCase
from django.urls import reverse

from .models import BlockedSender, ContactMessage, MembershipApplication, NewsletterSubscriber
from .tests import VALID
from .tests_helpers import human

User = get_user_model()


class BlockSenderTests(TestCase):
    def setUp(self):
        caches['antispam'].clear()
        self.admin = User.objects.create_user(
            username='adm', password='x', email='adm@x.org', nom='A', prenom='B', role='admin')
        self.message = ContactMessage.objects.create(
            name='Spam', last_name='Bot', email='Spammeur@Example.org', subject='other', message='Achetez !')
        self.client.force_login(self.admin)

    def block(self):
        return self.client.post(reverse('contact_message_block', args=[self.message.pk]))

    def test_block_button_is_shown_then_unblock_button(self):
        r = self.client.get(reverse('contact_message_detail', args=[self.message.pk]))
        self.assertContains(r, 'Bloquer cet expéditeur')
        self.block()
        r = self.client.get(reverse('contact_message_detail', args=[self.message.pk]))
        self.assertContains(r, 'Expéditeur bloqué')
        self.assertContains(r, 'Débloquer')
        self.assertNotContains(r, 'Bloquer cet expéditeur')

    def test_blocking_stores_the_address_in_lowercase_with_author(self):
        self.block()
        self.block()  # sans doublon
        blocked = BlockedSender.objects.get()
        self.assertEqual(blocked.email, 'spammeur@example.org')
        self.assertEqual(blocked.blocked_by, self.admin)
        self.assertEqual(ContactMessage.objects.count(), 1)  # le message reste consultable

    def test_blocked_address_cannot_use_any_public_form(self):
        self.block()
        contact = human({'name': 'S', 'last_name': 'B', 'email': 'SPAMMEUR@example.org', 'phone': '',
                         'subject': 'other', 'message': 'Encore'})
        r = self.client.post(reverse('contact'), contact, follow=True)
        self.assertContains(r, 'ne peut plus envoyer de formulaire')
        r = self.client.post(reverse('membership_apply'), human({**VALID, 'email': 'spammeur@example.org'}), follow=True)
        self.assertContains(r, 'ne peut plus envoyer de formulaire')
        r = self.client.post(reverse('newsletter_subscribe'), human({'email': 'spammeur@example.org'}), follow=True)
        self.assertContains(r, 'ne peut plus envoyer de formulaire')
        self.assertEqual(ContactMessage.objects.count(), 1)
        self.assertEqual(MembershipApplication.objects.count(), 0)
        self.assertEqual(NewsletterSubscriber.objects.count(), 0)

    def test_other_addresses_are_not_affected(self):
        self.block()
        r = self.client.post(reverse('contact'), human({
            'name': 'Awa', 'last_name': 'T', 'email': 'awa@example.org', 'phone': '',
            'subject': 'other', 'message': 'Bonjour'}))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(ContactMessage.objects.count(), 2)

    def test_unblock_restores_access(self):
        self.block()
        self.client.post(reverse('contact_message_unblock', args=[self.message.pk]))
        self.assertFalse(BlockedSender.objects.exists())
        r = self.client.post(reverse('newsletter_subscribe'), human({'email': 'spammeur@example.org'}))
        self.assertEqual(NewsletterSubscriber.objects.count(), 1)

    def test_only_post_and_only_moderators(self):
        self.assertEqual(self.client.get(reverse('contact_message_block', args=[self.message.pk])).status_code, 405)
        member = User.objects.create_user(
            username='mem', password='x', email='m@x.org', nom='M', prenom='N', role='membre')
        self.client.force_login(member)
        self.client.post(reverse('contact_message_block', args=[self.message.pk]))
        self.assertFalse(BlockedSender.objects.exists())


class BulkActionsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='adm', password='x', email='adm@x.org', nom='A', prenom='B', role='admin')
        self.client.force_login(self.admin)
        self.m = [ContactMessage.objects.create(name=f'N{i}', last_name='P', email=f'u{i}@example.org' if i < 3 else 'u0@example.org',
                                                subject='other', message='x') for i in range(4)]
        self.url = reverse('contact_message_bulk')

    def post(self, action, items, follow=False, **extra):
        return self.client.post(self.url, {'action': action, 'selected': [m.pk for m in items], **extra}, follow=follow)

    def test_list_has_checkboxes_and_no_individual_delete_button(self):
        r = self.client.get(reverse('contact_message_list'))
        self.assertContains(r, 'name="selected"', count=4)
        self.assertContains(r, 'Marquer comme lus')
        self.assertContains(r, 'Bloquer les expéditeurs')
        self.assertNotContains(r, reverse('contact_message_delete', args=[self.m[0].pk]))

    def test_mark_read_only_touches_the_selection_and_keeps_replied_status(self):
        self.m[1].status = ContactMessage.Status.REPLIED
        self.m[1].save()
        self.post('mark_read', self.m[:2])
        for m in self.m:
            m.refresh_from_db()
        self.assertTrue(self.m[0].is_read and self.m[1].is_read)
        self.assertEqual(self.m[0].status, ContactMessage.Status.READ)
        self.assertEqual(self.m[1].status, ContactMessage.Status.REPLIED)
        self.assertFalse(self.m[2].is_read)

    def test_block_selected_senders_once_per_address(self):
        self.post('block', [self.m[0], self.m[3]])      # même adresse
        self.assertEqual(list(BlockedSender.objects.values_list('email', flat=True)), ['u0@example.org'])
        self.assertEqual(ContactMessage.objects.count(), 4)
        r = self.client.get(reverse('contact_message_list'))
        self.assertContains(r, 'Bloqué')

    def test_delete_selected_only(self):
        self.post('delete', self.m[:2])
        self.assertEqual(ContactMessage.objects.count(), 2)

    def test_nothing_selected_changes_nothing(self):
        r = self.post('delete', [], follow=True)
        self.assertContains(r, 'Cochez au moins un message')
        self.assertEqual(ContactMessage.objects.count(), 4)

    def test_redirects_back_to_the_same_page_but_never_off_site(self):
        r = self.post('mark_read', self.m[:1], next='/users/contact-messages/?status=unread')
        self.assertRedirects(r, '/users/contact-messages/?status=unread', fetch_redirect_response=False)
        r = self.post('mark_read', self.m[:1], next='https://evil.example/')
        self.assertRedirects(r, reverse('contact_message_list'), fetch_redirect_response=False)

    def test_only_moderators_and_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        member = User.objects.create_user(
            username='mem', password='x', email='m@x.org', nom='M', prenom='N', role='membre')
        self.client.force_login(member)
        self.post('delete', self.m)
        self.assertEqual(ContactMessage.objects.count(), 4)


class SubscriberBulkTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='adm', password='x', email='adm@x.org', nom='A', prenom='B', role='admin')
        self.client.force_login(self.admin)
        self.subs = [NewsletterSubscriber.objects.create(email=f'Bot{i}@Example.org') for i in range(3)]
        self.url = reverse('newsletter_subscriber_bulk')

    def post(self, action, items, follow=False, **extra):
        return self.client.post(self.url, {'action': action, 'selected': [s.pk for s in items], **extra}, follow=follow)

    def active_ids(self):
        return set(NewsletterSubscriber.objects.filter(is_active=True).values_list('pk', flat=True))

    def test_list_has_checkboxes_and_no_delete_action(self):
        r = self.client.get(reverse('newsletter_list'))
        self.assertContains(r, 'name="selected"', count=3)
        self.assertContains(r, 'Désactiver')
        self.assertNotContains(r, 'value="delete"')

    def test_deactivate_and_reactivate_never_delete(self):
        self.post('deactivate', self.subs[:2])
        self.assertEqual(NewsletterSubscriber.objects.count(), 3)
        self.assertEqual(self.active_ids(), {self.subs[2].pk})
        self.assertFalse(BlockedSender.objects.exists())
        self.post('activate', self.subs[:1])
        self.assertEqual(self.active_ids(), {self.subs[0].pk, self.subs[2].pk})

    def test_deactivated_subscribers_receive_nothing(self):
        from . import mailing
        self.post('deactivate', self.subs[:2])
        active = NewsletterSubscriber.objects.filter(is_active=True)
        self.assertEqual([s.pk for s in active], [self.subs[2].pk])

    def test_deactivate_and_block_prevents_resubscription_and_can_be_undone(self):
        self.post('deactivate_block', self.subs[:2])
        self.assertEqual(sorted(BlockedSender.objects.values_list('email', flat=True)), ['bot0@example.org', 'bot1@example.org'])
        self.assertEqual(NewsletterSubscriber.objects.count(), 3)
        r = self.client.post(reverse('newsletter_subscribe'), human({'email': 'BOT0@example.org'}), follow=True)
        self.assertContains(r, 'ne peut plus envoyer de formulaire')
        self.assertFalse(NewsletterSubscriber.objects.get(pk=self.subs[0].pk).is_active)
        self.assertContains(self.client.get(reverse('newsletter_list')), 'Bloqué')
        self.post('unblock', self.subs[:2])
        self.assertFalse(BlockedSender.objects.exists())

    def test_status_filter(self):
        self.post('deactivate', self.subs[:1])
        self.assertContains(self.client.get(reverse('newsletter_list') + '?status=inactive'), 'name="selected"', count=1)
        self.assertContains(self.client.get(reverse('newsletter_list') + '?status=active'), 'name="selected"', count=2)

    def test_nothing_selected_and_unknown_action(self):
        r = self.post('deactivate', [], follow=True)
        self.assertContains(r, 'Cochez au moins un abonné')
        r = self.post('delete', self.subs, follow=True)          # la suppression n'existe plus
        self.assertContains(r, 'Action inconnue')
        self.assertEqual(NewsletterSubscriber.objects.count(), 3)
        self.assertEqual(len(self.active_ids()), 3)

    def test_redirect_stays_on_site(self):
        r = self.post('deactivate', self.subs[:1], next='https://evil.example/')
        self.assertRedirects(r, reverse('newsletter_list'), fetch_redirect_response=False)

    def test_only_moderators_and_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        member = User.objects.create_user(
            username='mem', password='x', email='m@x.org', nom='M', prenom='N', role='membre')
        self.client.force_login(member)
        self.post('deactivate', self.subs)
        self.assertEqual(len(self.active_ids()), 3)
