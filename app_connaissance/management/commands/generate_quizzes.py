from django.core.management.base import BaseCommand
from app_connaissance.models import KnowledgeItem
from app_connaissance.services import generate_quiz_for_knowledge

class Command(BaseCommand):
    help = 'Génère automatiquement des quiz pour toutes les connaissances qui n\'en ont pas.'

    def handle(self, *args, **options):
        self.stdout.write("Démarrage de la génération des quiz...")
        
        # On sélectionne les items qui n'ont pas de quiz associé
        # Note: knowledgeitem.quiz est un OneToOneField, donc on peut vérifier s'il est null
        # Mais le reverse relation OneToOneField est un peu particulier en Django ORM filter
        # On va iterer et checker hasattr pour être sûr ou filter(quiz__isnull=True)
        
        items = KnowledgeItem.objects.filter(quiz__isnull=True)
        count = items.count()
        self.stdout.write(f"{count} connaissances trouvées sans quiz.")
        
        generated = 0
        skipped = 0
        
        for item in items:
            self.stdout.write(f"Traitement de : {item.title}...")
            quiz = generate_quiz_for_knowledge(item)
            if quiz:
                generated += 1
                self.stdout.write(self.style.SUCCESS(f"  -> Quiz créé avec {quiz.questions.count()} questions."))
            else:
                skipped += 1
                self.stdout.write(self.style.WARNING("  -> Impossible de générer (contenu insuffisant ?)."))
                
        self.stdout.write(self.style.SUCCESS(f"Terminé. {generated} quiz générés, {skipped} ignorés."))
