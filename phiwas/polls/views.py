from django.shortcuts import render
from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. BDP = Big Dick Pille")

# Create your views here.
