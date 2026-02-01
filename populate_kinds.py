from app_connaissance.models import KnowledgeItem, KnowledgeKind

def run():
    print("Populating KnowledgeKind...")
    mapping = {}
    for value, label in KnowledgeItem.Kind.choices:
        kind, created = KnowledgeKind.objects.get_or_create(name=label)
        # We can store the value (slug/code) if we had a field for it, but for now we match by label.
        # Actually, the user might want to keep the 'value' as slug or similar.
        # Let's ensure slug matches the original value if possible, or just rely on auto-slugify.
        # The auto-slugify uses name. "Procédure" -> "procedure". "Vidéo" -> "video".
        # Original values: "procedure", "document", "video", "guide".
        # Labels: "Procédure", "Document", "Vidéo", "Guide".
        # So slugs should match closely.
        mapping[value] = kind
        print(f"  {label} -> {kind} (Created: {created})")

    print("Updating KnowledgeItems...")
    count = 0
    for item in KnowledgeItem.objects.all():
        if item.kind in mapping:
            item.new_kind = mapping[item.kind]
            item.save()
            count += 1
    print(f"Updated {count} items.")

if __name__ == "__main__":
    run()
