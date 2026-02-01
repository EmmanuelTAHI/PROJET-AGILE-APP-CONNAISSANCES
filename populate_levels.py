from app_connaissance.models import TrainingModule, TrainingLevel

def run():
    print("Populating TrainingLevel...")
    mapping = {}
    for value, label in TrainingModule.Level.choices:
        level_obj, created = TrainingLevel.objects.get_or_create(name=label)
        mapping[value] = level_obj
        print(f"  {label} -> {level_obj} (Created: {created})")

    print("Updating TrainingModules...")
    count = 0
    for item in TrainingModule.objects.all():
        if item.level in mapping:
            item.new_level = mapping[item.level]
            item.save()
            count += 1
    print(f"Updated {count} items.")

if __name__ == "__main__":
    run()
