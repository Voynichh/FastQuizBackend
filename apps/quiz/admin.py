from django import forms
from django.contrib import admin

from .models import Category, Choice, Question, QuizSession, SessionQuestion

CHOICES_PER_QUESTION = 4


class ChoiceInlineFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        active = [
            f.cleaned_data
            for f in self.forms
            if f.cleaned_data and not f.cleaned_data.get("DELETE")
        ]
        if len(active) != CHOICES_PER_QUESTION:
            raise forms.ValidationError(f"Her soru tam {CHOICES_PER_QUESTION} şıkka sahip olmalı.")
        if sum(1 for c in active if c.get("is_correct")) != 1:
            raise forms.ValidationError("Tam olarak bir şık doğru olarak işaretlenmeli.")


class ChoiceInline(admin.TabularInline):
    model = Choice
    formset = ChoiceInlineFormSet
    extra = CHOICES_PER_QUESTION
    max_num = CHOICES_PER_QUESTION


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_editable = ("order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "category", "difficulty", "is_active")
    list_filter = ("category", "difficulty", "is_active")
    search_fields = ("text",)
    inlines = [ChoiceInline]


class SessionQuestionInline(admin.TabularInline):
    model = SessionQuestion
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in SessionQuestion._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "status", "client_type", "total_score", "started_at")
    list_filter = ("status", "client_type", "category")
    readonly_fields = [f.name for f in QuizSession._meta.fields]
    inlines = [SessionQuestionInline]

    def has_add_permission(self, request):
        return False
