from django.contrib import admin
from .models import Story, Node, Choice, UserProgress


class NodeInline(admin.TabularInline):
    model = Node
    extra = 0
    fields = ("key", "title", "is_ending", "bg")
    show_change_link = True


class ChoiceInline(admin.TabularInline):
    model = Choice
    fk_name = "from_node"  # 讓 inline 顯示「從這個節點出發」的選項
    extra = 0
    fields = ("order", "text", "to_node", "condition", "effect")
    autocomplete_fields = ("to_node",)


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ("code", "title")
    search_fields = ("code", "title")
    inlines = [NodeInline]


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("story", "key", "title", "is_ending")
    list_filter = ("story", "is_ending")
    search_fields = ("story__code", "key", "title")
    inlines = [ChoiceInline]
    autocomplete_fields = ("story",)


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("story_code", "from_node", "to_node", "order", "text")
    list_filter = ("from_node__story",)
    search_fields = ("from_node__story__code", "from_node__key", "to_node__key", "text")
    autocomplete_fields = ("from_node", "to_node")

    def story_code(self, obj):
        return obj.from_node.story.code


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "story", "current_node")
    list_filter = ("story",)
    search_fields = ("user__username", "story__code")


# Register your models here.
