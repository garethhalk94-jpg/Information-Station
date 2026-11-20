from django.test import TestCase
from django.urls import reverse

from news_station.models import Article
from user_station.models import CustomUser


class CreateArticleTests(TestCase):
    def setUp(self):
        self.journalist = CustomUser.objects.create_user(
            "jane", "jane@example.com", "Pass12345!", role="journalist"
        )
        self.reader = CustomUser.objects.create_user(
            "rob", "rob@example.com", "Pass12345!", role="reader"
        )
        self.url = reverse("create_article")

    def test_journalist_can_create_article(self):
        self.client.force_login(self.journalist)
        response = self.client.post(
            self.url, {"title": "Hello", "content": "Body", "publisher": ""}
        )
        article = Article.objects.get(title="Hello")
        self.assertRedirects(
            response, reverse("article_detail", args=[article.pk])
        )
        self.assertEqual(article.author, self.journalist)
        self.assertFalse(article.approved)

    def test_reader_cannot_create_article(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


class EditDeleteArticleTests(TestCase):
    def setUp(self):
        self.owner = CustomUser.objects.create_user(
            "jane", "jane@example.com", "Pass12345!", role="journalist"
        )
        self.other = CustomUser.objects.create_user(
            "john", "john@example.com", "Pass12345!", role="journalist"
        )
        self.reader = CustomUser.objects.create_user(
            "reader", "reader@example.com", "Pass12345!", role="reader"
        )
        self.article = Article.objects.create(
            title="Original", content="Body", author=self.owner
        )

    def check_article_exists(self):
        self.assertTrue(Article.objects.filter(pk=self.article.pk).exists())

    def test_other_journalist_cannot_edit(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("edit_article", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_other_journalist_cannot_delete(self):
        self.client.force_login(self.other)
        response = self.client.post(
            reverse("delete_article", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.check_article_exists()

    def test_reader_cannot_edit(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            reverse("edit_article", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_reader_cannot_delete(self):
        self.client.force_login(self.reader)
        response = self.client.post(
            reverse("delete_article", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_owner_journalist_can_edit(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("edit_article", args=[self.article.pk]),
            {"title": "Updated", "content": "Body", "publisher": ""},
        )
        self.assertRedirects(
            response, reverse("article_detail", args=[self.article.pk])
        )
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated")

    def test_owner_journalist_can_delete(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("delete_article", args=[self.article.pk])
        )
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(
            Article.objects.filter(pk=self.article.pk).exists()
        )

    def test_delete_requires_post(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("delete_article", args=[self.article.pk])
        )
        self.assertEqual(response.status_code, 405)
        self.check_article_exists()
