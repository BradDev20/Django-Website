from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from . import models

def index(request):
    r = models.Recipe.objects.all()
    return render(request, "index.html", {"recipes": r[len(r)-3: len(r)], "title": "Welcome"})

def profile(request, username):
    try:
        author = models.Profile.objects.get(user__username=username)
    except models.Profile.DoesNotExist:
        return render(request, "404.html", {"title": "404 Not Found"})
    recipes = models.Recipe.objects.filter(author=author.user)
    return render(request, "profile.html", {"author": author, "recipes": recipes, "title": author.user.get_full_name})

def recipe(request, recipe_id):
    try:
        r = models.Recipe.objects.get(id=recipe_id)
    except models.Recipe.DoesNotExist:
        return render(request, '404.html', {"title": "404 Not Found"})
    return render(request, "recipe.html", {"recipe":r, "title": r.title})

def edit_recipe(request, recipe_id):

    try:
        r = models.Recipe.objects.get(id=recipe_id)
    except models.Recipe.DoesNotExist:
        return render(request, '404.html', {"title": "404 Not Found"})

    err_ing = []
    err_step = []
    errors = []
    new_ings = []
    ings = []
    steps = []

    steps_to_save = []
    ingredients_to_save = []
    new_ings_to_create = []

    def clean_existing_ing(ing, m):
        try:
            ing.full_clean()
            ingredients_to_save.append(ing)
            return True
        except ValidationError as e:
            msg = str(e.message_dict)
            msg = msg.replace(",", ";")
            for char in "[]'.":
                msg = msg.replace(char, '')
            err_ing.append(f"Error in Step {ing.step.order}, Ingredient {m}: {msg[1:len(msg) - 1]}")
            return False

    def clean_new_ing(ing, m):
        try:
            ing.full_clean()
            new_ings_to_create.append(ing)
            return True
        except ValidationError as e:
            msg = str(e.message_dict)
            msg = msg.replace(",", ";")
            for char in "[]'.":
                msg = msg.replace(char, '')
            err_ing.append(f"Error in Step {ing.step.order}, Ingredient {m}: {msg[1:len(msg) - 1]}")
            return False

    def clean_step(s):
        try:
            s.full_clean()
            steps_to_save.append(s)
            return True
        except ValidationError as e:
            msg = str(e.message_dict)
            msg = msg.replace(",", ";")
            for char in "[]'.":
                msg = msg.replace(char, '')
            err_step.append(f"Error in Step {s.order}: {msg[1:len(msg) - 1]}")
            return False

    def clean_info(r):
        try:
            r.full_clean()
            return True
        except ValidationError as e:
            msg = str(e.message_dict)
            msg = msg.replace(",", ";")
            for char in "[]'.":
                msg = msg.replace(char, '')
            errors.append(f"Error in recipe info: {msg[1:len(msg) - 1]}")
            return False

    if request.method == "POST":

        bad_request = False
        keys = request.POST.keys()

        # Check if the user sent a malformed request(possible with HTML editing)
        check_keys = ["title","description","preptime","cooktime","yield"]
        for k in check_keys:
            if k not in keys:
                bad_request = True

        r.title = request.POST.get("title")
        r.description = request.POST.get("description")
        r.prep_time_minutes = request.POST.get("preptime")
        r.cook_time_minutes = request.POST.get("cooktime")
        r.serves = request.POST.get("yield")

        ord = 1
        s_list = r.get_steps()
        for s in s_list:
            s_id = f"step{s.id}"
            s.description = request.POST.get(f"{s_id}desc")
            lst = []
            m = 0
            s_ings = s.ingredients.all()
            for ing in s_ings:
                m += 1
                ing_id = f"ing{ing.id}"

                #Check if the user sent a malformed request(possible with HTML editing)
                check_keys = [f"{s_id}{ing_id}amt", f"{s_id}{ing_id}unit", f"{s_id}{ing_id}name"]
                for k in check_keys:
                    if k not in keys:
                        bad_request = True

                ing.amount = request.POST.get(f"{s_id}{ing_id}amt")
                ing.unit = request.POST.get(f"{s_id}{ing_id}unit")
                ing.name = request.POST.get(f"{s_id}{ing_id}name")
                lst.append(ing)

                clean_existing_ing(ing, m)

            # Check if the user sent a malformed request(possible with HTML editing)
            check_keys = [f"{s_id}newamt", f"{s_id}newunit", f"{s_id}newname"]
            for k in check_keys:
                if k not in keys:
                    bad_request = True

            new_ing = models.Ingredient()
            new_ing.amount = request.POST.get(f"{s_id}newamt")
            new_ing.unit = request.POST.get(f"{s_id}newunit")
            new_ing.name = request.POST.get(f"{s_id}newname")
            new_ing.step = s

            # Logic:
            # If the user filled any new ingredient value, clean + save
            if any([new_ing.amount, (new_ing.unit or "").strip(), (new_ing.name or "").strip()]):
                if clean_new_ing(new_ing, m+1):
                    new_ings.append(models.Ingredient())
                else:
                    new_ings.append(new_ing)
            else:
                new_ings.append(new_ing)

            ings.append(lst)
            steps.append(s)
            ord += 1

            clean_step(s)

        check_keys = ["newstepnewdesc", "newstepnewamt", "newstepnewunit", "newstepnewname"]
        for k in check_keys:
            if k not in keys:
                bad_request = True

        new_step = models.Step(order=ord, recipe=r)
        new_ing = models.Ingredient(step=new_step)
        new_step.description = request.POST.get("newstepnewdesc")
        new_ing.amount = request.POST.get("newstepnewamt")
        new_ing.unit = request.POST.get("newstepnewunit")
        new_ing.name = request.POST.get("newstepnewname")

        nsi = (new_step, new_ing)

        #Logic:
        # If the new step's description is not empty:
        # Check if both the new ingredient and its step are valid

        if (new_step.description or "").strip():
            if any([new_ing.amount, (new_ing.unit or "").strip(), (new_ing.name or "").strip()]):
                clean_new_ing(new_ing, 1)
            try:
                new_step.full_clean()
            except ValidationError as e:
                msg = str(e.message_dict)
                msg = msg.replace(",", ";")
                for char in "[]'.":
                    msg = msg.replace(char, '')
                err_step.append(f"Error in Step {new_step.order}: {msg[1:len(msg) - 1]}")

        clean_info(r)

        if err_step:
            for err in err_step:
                errors.append(err)
        if err_ing:
            for err in err_ing:
                errors.append(err)
        if bad_request:
            errors.insert(0, "Error: Malformed request detected, going to a fallback")

        content = list(zip(steps, ings, new_ings))

        if not (errors or bad_request):
            r.save()
            if steps_to_save:
                models.Step.objects.bulk_update(steps_to_save, ['description'])
            if ingredients_to_save:
                models.Ingredient.objects.bulk_update(ingredients_to_save, ['amount', 'unit', 'name'])
            if new_step.description:
                new_step.save()
            if new_ings_to_create:
                models.Ingredient.objects.bulk_create(new_ings_to_create)

            return redirect('/recipe/'+(str)(recipe_id))
        else:
            return render(request, "edit.html",
                          {"recipe": r,
                           "title": r.title,
                           "steps_ings": content,
                           "new_step_ing" : nsi,
                           "errors": errors})
    elif request.method == "GET":
        ings = []
        new_ings = []
        steps = []
        i = 1
        s_list = r.get_steps()
        for s in s_list:
            lst = s.ingredients.all()

            ings.append(lst)
            steps.append(s)
            i += 1

            n = models.Ingredient(step=s)
            n.step = s
            new_ings.append(n)

        ns = models.Step(order=len(s_list), recipe=r)
        new_step_ing = (ns, models.Ingredient(step=ns))

        content = list(zip(steps, ings, new_ings))
        return render(request, "edit.html",
                    {"recipe": r,
                            "title": r.title,
                            "steps_ings": content,
                            "new_step_ing": new_step_ing,
                            "errors": []})

def search(request):
    return render(request, "search.html", {"recipes": models.Recipe.objects.all(), "title": "Search"})

def signin(request):
    return render(request, "login.html", { })