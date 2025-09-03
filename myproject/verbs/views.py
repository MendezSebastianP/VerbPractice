from django.shortcuts import render
from .models import UserVerb
from django.contrib.auth.decorators import login_required

@login_required(login_url="/users/login/")
def verbs_home(request):
    # Get UserVerb objects for the current logged-in user
    # (UserVerbs are initialized during user registration)
    user_verbs = UserVerb.objects.filter(user=request.user).select_related('verb')
    return render(request, 'verbs/verbs_home.html', {'verbs': user_verbs})

# def post_page(request, slug):
#     posts = Post.objects.get(slug=slug)
#     return render(request, 'posts/post_page.html', { 'post' : posts})

# @login_required(login_url="/users/login/")
# def post_new(request):
#     return render(request, 'posts/post_new.html')