"""
news_station/views.py
The article list and article detail pages.
"""

from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Article


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
