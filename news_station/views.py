"""
news_station/views.py
The article list and article detail pages.
"""

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST
# from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect

from .models import Article
from .forms import ArticleForm


def home(request):
    """Show a page of approved articles, newest first."""
    approved = Article.objects.filter(approved=True).select_related(
        "author", "publisher"
    )
    page_obj = Paginator(approved, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "news_station/home.html",
        {"articles": page_obj, "page_obj": page_obj},
    )


# ***** ARTICLE VIEWS - START *****

@login_required
@permission_required("news_station.add_article", raise_exception=True)
def my_articles(request):
    """
    List the logged-in journalist's articles.
    """

    articles = request.user.articles.select_related("publisher")
    return render(
        request, "news_station/my_articles.html", {"articles": articles}
    )


@login_required
@permission_required("news_station.add_article", raise_exception=True)
def create_article(request):
    """Create an article owned by the logged-in journalist."""

    if request.method == "POST":
        form = ArticleForm(request.POST, user=request.user)
        if form.is_valid():
            article = form.save()
            messages.success(request, "Article submitted for approval.")
            return redirect("article_detail", pk=article.pk)
    else:
        form = ArticleForm(user=request.user)

    return render(request, "news_station/create_article.html", {"form": form})


@login_required
@permission_required("news_station.change_article", raise_exception=True)
def edit_article(request, pk):
    """
    Edit an article's title, content or publisher.

    Journalists can edit their own articles; editors can edit any article
    """

    if request.user.is_editor:
        article = get_object_or_404(Article, pk=pk)
    else:
        article = get_object_or_404(Article, pk=pk, author=request.user)

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article, user=request.user)
        if form.is_valid():
            article = form.save(commit=False)
            if not request.user.is_editor:
                article.approved = False
                article.approved_by = None
            article.save()
            messages.success(request, "Article updated.")
            return redirect("article_detail", pk=article.pk)
    else:
        form = ArticleForm(instance=article, user=request.user)

    return render(
        request,
        "news_station/edit_article.html",
        {"form": form, "article": article},
    )


@login_required
@permission_required("news_station.delete_article", raise_exception=True)
@require_POST
def delete_article(request, pk):
    """
    Delete an article (POST only).
    """

    if request.user.is_editor:
        article = get_object_or_404(Article, pk=pk)
    else:
        article = get_object_or_404(Article, pk=pk, author=request.user)

    article.delete()
    messages.success(request, "Article deleted.")
    return redirect("home")


def article_detail(request, pk):
    """
    Show one article.

    Unapproved articles are only visible to their author and to editors;
    everyone else gets a 404, as if the article did not exist.
    """
    article = get_object_or_404(
        Article.objects.select_related("author", "publisher"), pk=pk
    )
    user = request.user
    can_see_unapproved = user.is_authenticated and (
        user == article.author or user.is_editor
    )
    if not article.approved and not can_see_unapproved:
        raise Http404("Article not found.")

    return render(
        request, "news_station/article_detail.html", {"article": article}
    )
