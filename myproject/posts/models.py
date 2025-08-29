from django.db import models

# Create your models here.
class Post(models.Model):
    title = models.CharField(max_length=60)
    body = models.TextField(max_length=1000)
    slug = models.SlugField()
    date = models.DateTimeField(auto_now_add=True)
    banner = models.ImageField(default='fall-back.jpg', blank=True)
    def __str__(self):
        return self.title