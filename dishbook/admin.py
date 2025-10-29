from django.contrib import admin
from . import models

# Register your models here.
class IngredientInline(admin.TabularInline):
    model = models.Ingredient
    extra = 1

class StepAdmin(admin.ModelAdmin):
    inlines = [IngredientInline]

class StepInline(admin.TabularInline):
    model = models.Step
    extra = 1
    ordering = ['order']


class RecipeAdmin(admin.ModelAdmin):
    inlines = [StepInline]

admin.site.register(models.Recipe, RecipeAdmin)
admin.site.register(models.Step, StepAdmin)
admin.site.register(models.Profile)