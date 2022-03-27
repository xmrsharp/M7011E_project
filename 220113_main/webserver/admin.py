
from django.contrib import admin

from .models import Profile, ProfileAndPlant
from django.contrib.auth.models import Group, User



admin.site.register(Profile)
admin.site.register(ProfileAndPlant)
admin.site.unregister(Group)



