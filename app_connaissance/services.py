import random
import re
from .models import KnowledgeItem, Quiz, QuizQuestion, QuizChoice

def generate_quiz_for_knowledge(item: KnowledgeItem) -> Quiz | None:
    """
    Génère automatiquement un quiz pour une connaissance donnée.
    Retourne le quiz créé ou None si le contenu est insuffisant.
    """
    if hasattr(item, "quiz"):
        return item.quiz

    # Extraction du contenu
    text = item.content
    # Nettoyage HTML basique
    text = re.sub(r'<[^>]+>', '', text)
    # Découpage en phrases (très simpliste)
    sentences = [s.strip() for s in re.split(r'[.!?]', text) if len(s.strip()) > 20]
    
    if len(sentences) < 2:
        return None
    
    # Sélectionner quelques phrases aléatoires
    selected_sentences = random.sample(sentences, min(5, len(sentences)))
    
    quiz = Quiz.objects.create(
        knowledge_item=item,
        titre=f"Quiz : {item.title}",
        seuil_reussite_pct=70
    )
    
    count = 0
    for i, sent in enumerate(selected_sentences):
        words = [w for w in sent.split() if len(w) > 4]
        if not words:
            continue
        
        # Mot à deviner (le plus long par défaut)
        target_word = max(words, key=len)
        question_text = sent.replace(target_word, "______")
        
        q = QuizQuestion.objects.create(
            quiz=quiz,
            enonce=f"Complétez : {question_text}",
            ordre=i+1
        )
        
        # Bonne réponse
        QuizChoice.objects.create(question=q, texte=target_word, is_correct=True)
        
        # Mauvaises réponses (mots aléatoires du texte)
        all_words = [w for w in text.split() if len(w) > 4 and w != target_word]
        # Nettoyage des mots (ponctuation)
        all_words = [re.sub(r'[^\w]', '', w) for w in all_words]
        all_words = [w for w in all_words if len(w) > 3] # Filtre court après nettoyage
        
        distractors = []
        if len(all_words) >= 3:
            distractors = random.sample(list(set(all_words)), min(3, len(set(all_words))))
        
        # Compléter si pas assez de distracteurs
        while len(distractors) < 3:
            fallback = ["Option A", "Option B", "Option C", "Option D"]
            distractors.append(fallback[len(distractors)])

        for d in distractors:
             QuizChoice.objects.create(question=q, texte=d, is_correct=False)
        
        count += 1
        
    if count == 0:
        # Si aucune question n'a pu être générée, on supprime le quiz vide
        quiz.delete()
        return None
        
    return quiz
