import math, re

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User

# Create your models here.

def reject_zero_or_negative_float(val):
    if val <= 0:
        raise ValidationError("Value must be greater than 0.")

def reject_zero(val):
    if val <= 0:
        raise ValidationError("Value must be greater than 0.")

def reject_non_standard_string(val):
    try:
        float(val)
        int(val)
        raise ValidationError("Value cannot be a number.")
    except ValueError:
        pass

    if val is None or val.strip() == "":
        raise ValidationError("Value cannot be empty.")

    if re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", val):
        raise ValidationError("Value cannot be something non-standard.")

def reject_big_files(val):

    if val.size > 64 * 1024 * 1024: #64 megabytes
        raise ValidationError("File cannot exceed 64 MB.")

    if not val.name.endswith(".png") or (not next(val.chunks())[0:4] == b'\x89\x50\x4e\x47'):
        raise ValidationError("File must be a PNG.")

class Tag(models.Model):
    name = models.CharField(max_length=32)

class Recipe(models.Model):

    title = models.CharField(max_length=64,validators=[reject_non_standard_string])
    photo = models.ImageField(upload_to="media/", null=True, blank=True, validators=[reject_big_files])
    description = models.TextField(validators=[reject_non_standard_string])
    prep_time_minutes = models.PositiveIntegerField()
    cook_time_minutes = models.PositiveIntegerField()
    serves = models.PositiveIntegerField(validators=[reject_zero])
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    copied_from = models.ForeignKey('self', blank=True, null=True, on_delete=models.SET_NULL, related_name='copies')
    featured_on = models.DateTimeField(max_length=256, null=True, blank=True)
    is_public = models.BooleanField(default=False)

    tags = models.ManyToManyField(Tag)

    def total_time_minutes(self):
        p = 0
        c = 0
        if isinstance(self.prep_time_minutes, int):
            p = self.prep_time_minutes
        if isinstance(self.cook_time_minutes, int):
            c = self.cook_time_minutes
        return p + c

    def get_copies(self):
        return models.Recipe.objects.filter(copied_from__title = self.title).count()

    def sorted_tags(self):
        return self.tags.order_by('name')

    def get_steps(self):
        return Step.objects.filter(recipe = self).order_by('order')

    def get_ingredients(self):
        steps = self.get_steps()
        ingredients = {}
        for step in steps:
            step_ing = Ingredient.objects.filter(step = step)
            for ingredient in step_ing:
                if (ingredient.name + "_" + ingredient.unit) not in ingredients.keys():
                    ingredients[ingredient.name + "_" + ingredient.unit] = (ingredient.name, ingredient.amount, ingredient.unit)
                else:
                    ingredients[ingredient.name + "_" + ingredient.unit] = (ingredient.name, ingredients[ingredient.name + "_" + ingredient.unit][1] + ingredient.amount, ingredient.unit)

        #print(ingredients)

        finallist = [""]
        for ing in ingredients:
            #print(ing)
            exists = False
            for val in range(len(finallist)):
                try:

                    i = finallist[val].index(ingredients[ing][0])
                    displayed_val = 0
                    if (ingredients[ing][1]).is_integer():
                        displayed_val = (int)(ingredients[ing][1])
                    else:
                        displayed_val = ingredients[ing][1]

                    if ingredients[ing][2] == "ct":
                        finallist[val] = (finallist[val][:i] + " and " +
                                          ((str)(displayed_val) + " " + ingredients[ing][0]))
                    else:
                        finallist[val] = (finallist[val][:i] + " and " +
                                          ((str)(displayed_val) + " " + ingredients[ing][2] + " " + ingredients[ing][0]))
                    exists = True

                except ValueError:
                    continue

            if not exists:
                displayed_val = 0
                if (ingredients[ing][1]).is_integer():
                    displayed_val = (int)(ingredients[ing][1])
                else:
                    displayed_val = round(ingredients[ing][1], 2)

                if ingredients[ing][2] == "ct":
                    finallist.append((str)(displayed_val) + " " + ingredients[ing][0])
                else:
                    finallist.append((str)(displayed_val) + " " + ingredients[ing][2] + " " + ingredients[ing][0])

        #print(finallist)
        return finallist


class Step(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    description = models.TextField(validators=[reject_non_standard_string])

    def get_rows(self):
        if not self.description:
            return 1
        return math.ceil(len(self.description)/50.0)

class Ingredient(models.Model):
    step = models.ForeignKey(Step, on_delete=models.CASCADE, related_name="ingredients")
    amount = models.FloatField(validators=[reject_zero_or_negative_float])
    unit = models.CharField(max_length=16, validators=[reject_non_standard_string])
    name = models.CharField(max_length=50, validators=[reject_non_standard_string])

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    photo = models.ImageField(upload_to="media/", null=True, blank=True)
    bio = models.TextField(null=True, blank=True)