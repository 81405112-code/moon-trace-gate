from django.conf import settings
from django.db import models


class Story(models.Model):
    code = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Node(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name="nodes")
    key = models.SlugField(max_length=80)
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_ending = models.BooleanField(default=False)
    bg = models.CharField(max_length=255, blank=True)  # 例如 "stories/bg/mistwood.jpg"


    class Meta:
        unique_together = ("story", "key")

    def __str__(self):
        return f"{self.story.code}:{self.key}"


class Choice(models.Model):
    from_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=200)
    to_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="incoming")
    order = models.PositiveIntegerField(default=0)
    condition = models.JSONField(default=dict, blank=True)
    effect = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.from_node} -> {self.to_node} ({self.text})"


class UserProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    story = models.ForeignKey(Story, on_delete=models.CASCADE)
    current_node = models.ForeignKey(Node, on_delete=models.CASCADE)
    vars = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "story")


# Create your models here.
