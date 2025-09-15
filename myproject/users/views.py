from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from verbs.services import init_user_verbs
from word_training.services import init_user_words

# Create your views here.
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            init_user_verbs(user, n=10)
            init_user_words(user, n=10)
            login(request, user)
            return redirect("verbs:verbstraining")
    else:
        form = UserCreationForm()
    return render(request, "users/register.html", { "form" : form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if "next" in request.POST:
                return redirect(request.POST.get('next'))
            else:
                return redirect("verbs:verbstraining")
    else:
        form = AuthenticationForm()
    return render(request, "users/login.html", { "form" : form})

def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("users:login")
    

# Verb functions

# def load_first_verbs(form):
    