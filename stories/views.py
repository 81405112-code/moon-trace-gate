from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render

from .models import Story, Node, Choice, UserProgress


LABELS = {"shard": "月痕碎片", "mana": "法力", "honor": "名聲"}


def fmt_key(key: str) -> str:
    return LABELS.get(key, key)


def condition_text(condition: dict) -> str:
    if not condition:
        return ""
    parts = []
    for k, v in condition.items():
        if k.endswith("_gte"):
            base = k[:-4]
            parts.append(f"{fmt_key(base)} ≥ {v}")
        else:
            if k == "shard" and isinstance(v, bool):
                parts.append("持有月痕碎片" if v else "未持有月痕碎片")
            else:
                parts.append(f"{fmt_key(k)} = {v}")
    return "、".join(parts)


def unmet_reasons(vars: dict, condition: dict) -> list[str]:
    vars = vars or {}
    condition = condition or {}
    reasons = []
    for k, v in condition.items():
        if k.endswith("_gte"):
            base = k[:-4]
            if int(vars.get(base, 0)) < int(v):
                reasons.append(f"{fmt_key(base)} ≥ {v}")
        else:
            if vars.get(k) != v:
                if k == "shard" and isinstance(v, bool):
                    reasons.append("需要持有月痕碎片" if v else "需要未持有月痕碎片")
                else:
                    reasons.append(f"{fmt_key(k)} = {v}")
    return reasons


def check_condition(vars: dict, condition: dict) -> bool:
    return len(unmet_reasons(vars, condition)) == 0


def apply_effect(vars: dict, effect: dict) -> dict:
    vars = dict(vars or {})
    effect = effect or {}
    for k, v in effect.items():
        if isinstance(v, int) and isinstance(vars.get(k, 0), int):
            vars[k] = int(vars.get(k, 0)) + v
        else:
            vars[k] = v
    return vars


@login_required
def play(request, code: str):
    story = get_object_or_404(Story, code=code)

    start_node = Node.objects.filter(story=story, key="start").first() or Node.objects.filter(story=story).order_by("id").first()
    if not start_node:
        return HttpResponseBadRequest("Story has no nodes.")

    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        story=story,
        defaults={"current_node": start_node, "vars": {}},
    )
    if created or progress.current_node.story_id != story.id:
        progress.current_node = start_node
        progress.vars = {}
        progress.save()

    node = progress.current_node
    vars_ = progress.vars or {}

    choice_rows = []
    for c in node.choices.all().order_by("order", "id"):
        cond = c.condition or {}
        unmet = unmet_reasons(vars_, cond)
        ok = (len(unmet) == 0)
        hint = ""
        if cond:
            hint = ("缺少：" + "、".join(unmet)) if not ok else ("條件：" + condition_text(cond))
        choice_rows.append({"choice": c, "ok": ok, "hint": hint})

    return render(request, "stories/play.html", {
        "story": story,
        "node": node,
        "vars": vars_,
        "choices": choice_rows,
    })


@login_required
def choose(request, choice_id: int):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required.")

    choice = get_object_or_404(Choice, id=choice_id)
    story = choice.from_node.story

    progress = get_object_or_404(UserProgress, user=request.user, story=story)
    vars_ = progress.vars or {}

    if not check_condition(vars_, choice.condition or {}):
        return HttpResponseBadRequest("Condition not met.")

    progress.vars = apply_effect(vars_, choice.effect or {})
    progress.current_node = choice.to_node
    progress.save()

    # ✅ HTMX 請求：回傳 partial（只換左下角 box）
    if request.headers.get("HX-Request") == "true":
        node = progress.current_node
        vars_ = progress.vars or {}

        choice_rows = []
        for c in node.choices.all().order_by("order", "id"):
            cond = c.condition or {}
            unmet = unmet_reasons(vars_, cond)
            ok = (len(unmet) == 0)
            hint = ""
            if cond:
                hint = ("缺少：" + "、".join(unmet)) if not ok else ("條件：" + condition_text(cond))
            choice_rows.append({"choice": c, "ok": ok, "hint": hint})

        return render(request, "stories/_box.html", {
            "story": story,
            "node": node,
            "vars": vars_,
            "choices": choice_rows,
        })

    # 一般請求仍用 redirect
    return redirect("stories:play", code=story.code)


@login_required
def restart(request, code: str):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required.")

    story = get_object_or_404(Story, code=code)

    start_node = (
        Node.objects.filter(story=story, key="start").first()
        or Node.objects.filter(story=story).order_by("id").first()
    )
    if not start_node:
        return HttpResponseBadRequest("Story has no nodes.")

    progress, _ = UserProgress.objects.get_or_create(
        user=request.user,
        story=story,
        defaults={"current_node": start_node, "vars": {}},
    )

    progress.current_node = start_node
    progress.vars = {}
    progress.save()

    # ✅ HTMX：只回傳 box
    if request.headers.get("HX-Request") == "true":
        node = progress.current_node
        vars_ = progress.vars or {}

        choice_rows = []
        for c in node.choices.all().order_by("order", "id"):
            cond = c.condition or {}
            unmet = unmet_reasons(vars_, cond)
            ok = (len(unmet) == 0)
            hint = ""
            if cond:
                hint = ("缺少：" + "、".join(unmet)) if not ok else ("條件：" + condition_text(cond))
            choice_rows.append({"choice": c, "ok": ok, "hint": hint})

        return render(request, "stories/_box.html", {
            "story": story,
            "node": node,
            "vars": vars_,
            "choices": choice_rows,
        })

    return redirect("stories:play", code=story.code)

def home(request):
    stories = list(Story.objects.all().order_by("title"))

    for s in stories:
        start_node = Node.objects.filter(story=s, key="start").only("bg").first()
        s.cover_bg = (start_node.bg if start_node and start_node.bg else "")

    home_bg = stories[0].cover_bg if stories and getattr(stories[0], "cover_bg", "") else ""

    return render(request, "stories/home.html", {
        "stories": stories,
        "home_bg": home_bg,
    })

