from datetime import datetime
import os
from uuid import uuid4
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from PIL import Image






# Extending User Model Using a One-To-One Link
class Profile(models.Model):
    def path_and_rename(instance, filename):
        upload_to = 'profile_images'
        ext = filename.split('.')[-1]
        # get filename
        if instance.pk:
            filename = '{}.{}'.format(instance.pk, ext)
        else:
        # set filename as random string
            filename = '{}.{}'.format(uuid4().hex, ext)
        # return the whole path to the file
        return os.path.join(upload_to, filename)

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_logged_in = models.BooleanField(default=False)
    avatar = models.ImageField(
        default='default.jpg', upload_to=path_and_rename)
    bio = models.TextField()

    #def __str__(self):
    #    return self.user.username
    #    # resizing images

    def save(self, *args, **kwargs):
        super().save()

        img = Image.open(self.avatar.path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        if img.height > 100 or img.width > 100:
            new_img = (100, 100)
            img.thumbnail(new_img)
            img.save(self.avatar.path)

# These records are to be updated after a succesfull creation of prosumer in plant_server is returned.
# Create prosumer -> ok -> update this field with user.
# Or have admin fetch all plants -> and connect user to one of the fields - giving access.
class ProfileAndPlant(models.Model):
    user_id = models.ForeignKey(Profile, on_delete=models.CASCADE)
    plant_id = models.IntegerField()                                        #recieve confirmation of prosumer creation by plant_server.
    plant_type = models.CharField(max_length=50)
    
        


"""
class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)

    def __str__(self):
        return self.question_text

    def delete_q(self):
        self.question_text = ""


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text


class ProSumer(models.Model):
    blackout = models.BooleanField(User)"""








