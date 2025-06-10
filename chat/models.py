from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)


class Thread(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    bot_thread_id = models.CharField(max_length=256)