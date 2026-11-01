from django.template import Context, Template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from articles.models import Article
from site_web.sanitize import clean_html, plain_text


class CleanHtmlTests(SimpleTestCase):
    def test_dangerous_content_is_removed(self):
        for bad, gone in [
            ('<p>ok</p><script>alert(1)</script>', 'script'),
            ('<img src=x onerror="alert(1)">', 'onerror'),
            ('<a href="javascript:alert(1)">clic</a>', 'javascript'),
            ('<iframe src="https://evil.example"></iframe>', 'iframe'),
            ('<p style="background:url(javascript:alert(1))">x</p>', 'url('),
            ('<a href="data:text/html;base64,PHNjcmlwdD4=">x</a>', 'data:'),
            ('<svg onload=alert(1)>', 'svg'),
        ]:
            self.assertNotIn(gone, clean_html(bad), bad)

    def test_editor_formatting_is_kept(self):
        source = ('<h3 style="text-align: center;">Titre</h3><p>Du <span style="color: rgb(255, 0, 0); font-size: 14px;">rouge</span>, '
                  '<font color="#336699">bleu</font> et <a href="https://exemple.org" target="_blank">un lien</a></p><ul><li>un</li></ul>')
        self.assertEqual(clean_html(source), source)

    def test_word_junk_and_unknown_style_are_dropped_but_text_stays(self):
        out = clean_html('<p>Texte<o:p></o:p></p><div style="--tw-ring: 1">suite</div>')
        self.assertIn('Texte', out)
        self.assertIn('suite', out)
        self.assertNotIn('o:p', out)
        self.assertNotIn('--tw', out)
        self.assertEqual(clean_html('<p style="text-align: center; --tw-x: 1">x</p>'), '<p style="text-align: center;">x</p>')

    def test_font_names_in_quotes_survive(self):
        out = clean_html('<span style="font-family: &quot;Times New Roman&quot;, serif; color: red">x</span>')
        self.assertIn('Times New Roman', out)
        self.assertIn('color: red', out)

    def test_empty_values(self):
        self.assertEqual(clean_html(None), '')
        self.assertEqual(clean_html(''), '')

    def test_plain_text_is_escaped_by_the_template(self):
        self.assertEqual(plain_text('<i>Guerre</i> &amp; paix'), 'Guerre & paix')
        html = Template('{% load clean_tags %}{{ t|plain_text }}').render(Context({'t': '<b>x</b> &lt;script&gt;'}))
        self.assertEqual(html, 'x &lt;script&gt;')


class PublicPagesAreSanitizedTests(TestCase):
    def test_article_content_and_title_cannot_run_scripts(self):
        a = Article.objects.create(title='<script>alert(9)</script>Titre', article_type='analyse', status='published',
                                   content='<p>Corps</p><script>alert(1)</script><img src=x onerror=alert(2)>')
        html = self.client.get(reverse('public_article_detail', args=[a.slug])).content.decode()
        self.assertIn('<p>Corps</p>', html)
        self.assertNotIn('alert(1)', html)
        self.assertNotIn('onerror', html)
        listing = self.client.get(reverse('public_article_list')).content.decode()
        self.assertNotIn('<script>alert(9)', listing)
