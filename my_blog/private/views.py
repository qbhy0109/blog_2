from django.shortcuts import render
from django.http import HttpResponse
from .models import PrivateArticlePost

# Create your views here.


def article_list(request):
    articles = PrivateArticlePost.objects.all()
    context = {'articles': articles}
    return render(request, 'private/list.html', context)


