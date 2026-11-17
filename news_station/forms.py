from django import forms

from .models import Article


class ArticleForm(forms.ModelForm):
    """Form for journalists to create or edit an article."""

    class Meta:
        model = Article
        fields = ["title", "content", "publisher"]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.instance.author = user
        # Offer the author's publishers (not the editor's, when editing).
        author = self.instance.author
        self.fields["publisher"].queryset = author.publishers_written_for.all()
        self.fields["publisher"].empty_label = "Independent (no publisher)"
