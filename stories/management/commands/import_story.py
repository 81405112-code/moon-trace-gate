import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stories.models import Story, Node, Choice


class Command(BaseCommand):
    help = "Import an interactive story from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to story JSON file")

    @transaction.atomic
    def handle(self, *args, **options):
        json_path = Path(options["json_path"])
        if not json_path.exists():
            raise CommandError(f"File not found: {json_path}")

        # 讀 JSON（UTF-8）
        raw = json_path.read_text(encoding="utf-8-sig")
        data = json.loads(raw)

        story_data = data.get("story")
        if not story_data:
            raise CommandError("JSON missing 'story' object")

        code = story_data.get("code")
        title = story_data.get("title")
        if not code or not title:
            raise CommandError("'story.code' and 'story.title' are required")

        story, _ = Story.objects.update_or_create(
            code=code,
            defaults={"title": title, "description": story_data.get("description", "")},
        )

        # Nodes
        nodes_data = data.get("nodes", [])
        if not isinstance(nodes_data, list) or not nodes_data:
            raise CommandError("'nodes' must be a non-empty list")

        node_map = {}
        for n in nodes_data:
            key = n.get("key")
            body = n.get("body")
            if not key or body is None:
                raise CommandError("Each node requires 'key' and 'body'")

            node, _ = Node.objects.update_or_create(
                story=story,
                key=key,
                defaults={
                    "title": n.get("title", ""),
                    "body": body,
                    "is_ending": bool(n.get("is_ending", False)),
                    "bg": n.get("bg", ""),
                },
            )
            node_map[key] = node

        # Choices
        choices_data = data.get("choices", [])
        if not isinstance(choices_data, list):
            raise CommandError("'choices' must be a list")

        # 清掉舊的（此故事）
        deleted = Choice.objects.filter(from_node__story=story).delete()[0]

        created = 0
        for c in choices_data:
            from_key = c.get("from")
            to_key = c.get("to")
            text = c.get("text")
            if not from_key or not to_key or not text:
                raise CommandError("Each choice requires 'from', 'to', 'text'")

            if from_key not in node_map or to_key not in node_map:
                raise CommandError(f"Choice references missing node: {from_key} -> {to_key}")

            Choice.objects.create(
                from_node=node_map[from_key],
                to_node=node_map[to_key],
                text=text,
                order=int(c.get("order", 0)),
                condition=c.get("condition", {}) or {},
                effect=c.get("effect", {}) or {},
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported story '{story.title}' (code={story.code}) "
            f"nodes={len(node_map)} choices_created={created} choices_deleted={deleted}"
        ))
