import re
import random
import string


def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def unique_suffix() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
