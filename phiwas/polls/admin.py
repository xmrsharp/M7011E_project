from django.contrib import admin
from .models import Question
from .models import Profile

admin.site.register(Profile)
admin.site.register(Question)
