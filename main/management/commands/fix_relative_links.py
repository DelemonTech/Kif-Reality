import html
import re

from django.core.management.base import BaseCommand
from main.models import BlogPost

# <a href="../../../../">…</a> — pasted editor links. From /blogs/<slug>/ they
# resolve to the home page, and SEO crawlers flag the empty ones as
# "Links With No Anchor Text".
RELATIVE_LINK = re.compile(
    r'<a\b[^>]*?\bhref\s*=\s*(["\'])(?:\.\./)+\1[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)
HREF = re.compile(r'(\bhref\s*=\s*)(["\'])(?:\.\./)+\2', re.IGNORECASE)


def visible_text(fragment):
    text = html.unescape(re.sub(r'<[^>]+>', '', fragment))
    return text.replace('\xa0', ' ').strip()


def fix(content):
    """Return (new_content, removed_empty, repointed)."""
    removed = repointed = 0

    def replace(match):
        nonlocal removed, repointed
        inner = match.group(2)
        if not visible_text(inner) and '<img' not in inner.lower():
            removed += 1
            return inner  # drop the empty link, keep any whitespace/markup
        repointed += 1
        # Same destination as before (the home page), as a valid absolute URL.
        return HREF.sub(r'\1\2/\2', match.group(0), count=1)

    return RELATIVE_LINK.sub(replace, content), removed, repointed


class Command(BaseCommand):
    help = "Find blog links like href=\"../../../../\"; with --apply, remove empty ones and point the rest to /"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help="Save changes (default is a dry run)")

    def handle(self, *args, **options):
        apply = options['apply']
        posts = BlogPost.objects.filter(content__contains='../').only('id', 'slug', 'content')
        total_removed = total_repointed = changed = 0

        for post in posts:
            new_content, removed, repointed = fix(post.content)
            if not (removed or repointed):
                continue
            changed += 1
            total_removed += removed
            total_repointed += repointed
            self.stdout.write(f"/blogs/{post.slug}/  empty links removed: {removed}, links repointed to /: {repointed}")
            for m in RELATIVE_LINK.finditer(post.content):
                label = visible_text(m.group(2)) or '(no text)'
                self.stdout.write(f"    - {label[:70]}")
            if apply:
                # .update() so updated_at and save() side effects are untouched
                BlogPost.objects.filter(pk=post.pk).update(content=new_content)

        verb = "Fixed" if apply else "Would fix"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {changed} post(s): {total_removed} empty link(s) removed, {total_repointed} repointed."
        ))
        if not apply and changed:
            self.stdout.write("Dry run only. Re-run with --apply to save.")
