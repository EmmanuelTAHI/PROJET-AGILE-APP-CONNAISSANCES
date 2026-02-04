# Implémentation Technique du Plan d'Intégration Dynamique

## Vue d'ensemble

Cette implémentation améliore le système de plan d'intégration pour qu'il s'affiche de manière **dynamique en fonction du département et du poste de l'utilisateur connecté**, conformément au cahier des charges.

## Fonctionnalités Implémentées

### 1. Récupération Dynamique du Plan

**Fichier**: `app_connaissance/views.py` - Fonction `_get_user_plan()`

```python
def _get_user_plan(request: HttpRequest) -> PlanIntegration | None:
    """Retourne le plan d'intégration lié au poste de l'utilisateur (département + poste), ou None."""
    if not getattr(request.user, "is_authenticated", False):
        return None
    profile = (
        UserProfile.objects.filter(user=request.user)
        .select_related("department", "poste", "poste__plan_integration")
        .first()
    )
    if not profile or not profile.poste_id:
        return None
    return getattr(profile.poste, "plan_integration", None)
```

**Logique**:
- Récupère le profil de l'utilisateur connecté
- Vérifie si l'utilisateur a un poste assigné
- Retourne le plan d'intégration lié à ce poste
- Si pas de plan → retourne `None`

### 2. Calcul de Progression Amélioré

**Fichier**: `app_connaissance/views.py` - Fonction `_progress_for_plan()`

**Améliorations**:
- **Inclusion des connaissances**: Précharge les connaissances liées aux modules
- **Optimisation des requêtes**: Utilise `prefetch_related` pour éviter les N+1 queries
- **Structure enrichie**: Ajoute les connaissances dans les données de progression

```python
modules = list(
    plan.modules.prefetch_related(
        "quiz", 
        "quiz__questions", 
        "quiz__questions__choices", 
        "steps",
        "knowledge_links",              # NOUVEAU
        "knowledge_links__knowledge_item",  # NOUVEAU
        "knowledge_links__knowledge_item__versions"  # NOUVEAU
    )
    .order_by("ordre")
)
```

### 3. Affichage Dynamique des Connaissances

**Fichier**: `app_connaissance/templates/onboarding/plan_personnel.html`

**Nouvelles fonctionnalités**:
- **Affichage du contexte**: Département et poste de l'utilisateur
- **Connaissances associées**: Liste des connaissances liées à chaque module
- **Statuts visuels**: Badges pour l'état de validation des connaissances

```html
{# Contexte département et poste #}
{% if profile %}
  <span class="mt-2 block font-medium text-slate-700">
    {% if profile.department %}Département : {{ profile.department.name }}{% endif %}
    {% if profile.poste %} • Poste : {{ profile.poste.intitule }}{% endif %}
  </span>
{% endif %}

{# Connaissances associées au module #}
{% if item.knowledge_items %}
  <div class="mt-4 space-y-2 rounded-xl border border-blue-100 bg-blue-50/50 p-4">
    <div class="text-xs font-semibold uppercase tracking-wider text-blue-500">Connaissances associées</div>
    <ul class="space-y-2">
      {% for knowledge_data in item.knowledge_items %}
        <!-- Affichage des connaissances avec liens et statuts -->
      {% endfor %}
    </ul>
  </div>
{% endif %}
```

### 4. Script de Démonstration

**Fichier**: `app_connaissance/management/commands/populate_demo_plans.py`

**Fonctionnalités**:
- Crée automatiquement des plans d'intégration pour tous les postes existants
- Génère des modules cohérents selon le type de poste
- Crée des connaissances liées à chaque module
- Associe les plans aux postes correspondants

## Flux de Fonctionnement

### 1. Connexion Utilisateur
1. L'utilisateur se connecte avec son email/mot de passe
2. Le système récupère son profil (`UserProfile`)
3. Le profil contient: `department`, `poste`, `role`

### 2. Accès au Plan d'Intégration
1. L'utilisateur accède à `/integration/mon-plan/`
2. La vue `plan_integration_personnel()` est appelée
3. `_get_user_plan()` récupère le plan lié à son poste
4. Si pas de plan → redirection vers les étapes génériques

### 3. Affichage du Plan
1. `_progress_for_plan()` calcule la progression complète
2. Le template affiche:
   - En-tête avec contexte (département + poste)
   - Barre de progression globale
   - Modules avec sous-étapes
   - Connaissances associées à chaque module
   - Quiz et statuts de validation

### 4. Interaction Utilisateur
1. L'utilisateur coche les sous-étapes (AJAX)
2. L'utilisateur clique sur les connaissances pour les consulter
3. L'utilisateur passe les quiz pour valider les modules
4. La progression est mise à jour en temps réel

## Structure des Données

### Modèles Impliqués

```python
# UserProfile - Profil utilisateur
UserProfile {
    user: User
    department: Department
    poste: Poste
    role: str
}

# Poste - Poste avec plan d'intégration
Poste {
    intitule: str
    department: Department
    plan_integration: PlanIntegration
}

# PlanIntegration - Plan de formation
PlanIntegration {
    titre: str
    description: str
    duree_estimee_jours: int
    modules: Module[]
}

# Module - Section du plan
Module {
    titre: str
    ordre: int
    plan: PlanIntegration
    steps: ModuleStep[]
    knowledge_links: ModuleKnowledgeItem[]
}

# ModuleKnowledgeItem - Lien module-connaissance
ModuleKnowledgeItem {
    module: Module
    knowledge_item: KnowledgeItem
    ordre: int
}
```

## Sécurité et Contrôle d'Accès

### Vérifications Implémentées

1. **Authentification requise**: `@frontend_login_required`
2. **Appartenance au plan**: Vérification que le quiz/appartient bien au plan de l'utilisateur
3. **Isolation des données**: Un utilisateur ne voit que son propre plan

```python
# Vérification dans quiz_take()
plan = _get_user_plan(request)
if not plan or not quiz.module_id or getattr(quiz.module, "plan_id", None) != plan.id:
    messages.error(request, "Ce quiz ne fait pas partie de votre plan d'intégration.")
    return redirect("onboarding_home")
```

## Avantages de l'Implémentation

### 1. **Personnalisation Complète**
- Chaque employé voit uniquement son plan personnalisé
- Le contenu s'adapte automatiquement à son poste et département

### 2. **Performance Optimisée**
- Utilisation de `select_related` et `prefetch_related`
- Évite les requêtes N+1
- Chargement efficace des données

### 3. **Expérience Utilisateur Riche**
- Affichage clair du contexte (département + poste)
- Accès direct aux connaissances pertinentes
- Suivi de progression en temps réel

### 4. **Extensibilité**
- Facile à ajouter de nouveaux types de contenu
- Structure modulaire pour les évolutions futures
- Compatible avec le système de versionnement

## Tests et Validation

### Scénarios de Test

1. **Employé avec plan**: Vérifie l'affichage correct de son plan
2. **Employé sans plan**: Vérifie la redirection vers les étapes génériques
3. **Manager**: Vérifie l'accès aux plans de son équipe
4. **Admin**: Vérifie l'accès à tous les plans

### Commande de Test

```bash
# Créer des données de démonstration
python manage.py populate_demo_plans

# Vérifier les plans créés
python manage.py shell
>>> from app_connaissance.models import PlanIntegration, Poste
>>> PlanIntegration.objects.all()
>>> Poste.objects.filter(plan_integration__isnull=False)
```

## Conformité au Cahier des Charges

✅ **Plan personnalisé selon poste/département**: Implémenté via `_get_user_plan()`
✅ **Affectation automatique**: Via la liaison Poste ↔ PlanIntegration  
✅ **Modules structurés**: Avec sous-étapes et connaissances
✅ **Suivi de progression**: Avec pourcentage et statuts
✅ **Quiz d'évaluation**: Intégrés aux modules
✅ **Connaissances liées**: Affichées dynamiquement par module

## Conclusion

Cette implémentation fournit une solution complète et robuste pour le plan d'intégration dynamique, répondant à toutes les exigences du cahier des charges tout en offrant une excellente expérience utilisateur et des performances optimales.
