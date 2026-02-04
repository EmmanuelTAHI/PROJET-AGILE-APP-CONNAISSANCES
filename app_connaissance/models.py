from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.template.defaultfilters import slugify


class Entreprise(models.Model):
    """Organisation cliente (multi-tenant SaaS)."""
    name = models.CharField(max_length=120)
    logo = models.ImageField(upload_to="entreprise_logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True, blank=True)
    entreprise = models.ForeignKey(
        Entreprise, on_delete=models.CASCADE, related_name="departments", null=True, blank=True
    )
    manager = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_departments"
    )
    description = models.CharField(max_length=280, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Competence(models.Model):
    """Savoir-faire ou aptitude (lié aux postes et connaissances)."""
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, default="")
    categorie = models.CharField(max_length=60, blank=True, default="")
    niveau = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class PlanIntegration(models.Model):
    """Parcours de formation pour un poste."""
    titre = models.CharField(max_length=180)
    description = models.TextField(blank=True, default="")
    duree_estimee_jours = models.PositiveIntegerField(default=0, help_text="Durée estimée en jours")

    class Meta:
        ordering = ["titre"]

    def __str__(self) -> str:
        return self.titre


class Poste(models.Model):
    """Fonction au sein d'un département (intitulé, missions, compétences, plan d'intégration)."""
    intitule = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="postes"
    )
    plan_integration = models.ForeignKey(
        PlanIntegration, on_delete=models.SET_NULL, null=True, blank=True, related_name="postes"
    )
    competences = models.ManyToManyField(Competence, blank=True, related_name="postes")

    class Meta:
        ordering = ["intitule"]
        unique_together = [["department", "intitule"]]

    def __str__(self) -> str:
        return self.intitule


class Module(models.Model):
    """Section thématique d'un plan d'intégration (ex: Module 1 - Découverte)."""
    titre = models.CharField(max_length=140)
    ordre = models.PositiveIntegerField(default=1)
    plan = models.ForeignKey(
        PlanIntegration, on_delete=models.CASCADE, related_name="modules"
    )
    duree_jours = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["plan", "ordre"]

    def __str__(self) -> str:
        return self.titre


class ModuleStep(models.Model):
    """Sous-étape d'un module (case à cocher pour l'utilisateur)."""
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="steps"
    )
    titre = models.CharField(max_length=200)
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["module", "ordre"]
        unique_together = [["module", "ordre"]]

    def __str__(self) -> str:
        return f"{self.module.titre} — {self.titre}"


class UserModuleStepCompletion(models.Model):
    """Suivi : sous-étape cochée par un utilisateur."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="module_step_completions"
    )
    module_step = models.ForeignKey(
        ModuleStep, on_delete=models.CASCADE, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["user", "module_step"]]

    def __str__(self) -> str:
        return f"{self.user} — {self.module_step}"


class Quiz(models.Model):
    """Quiz associé à un module du plan d'intégration ou à une connaissance."""
    module = models.OneToOneField(
        Module, on_delete=models.CASCADE, related_name="quiz", null=True, blank=True
    )
    knowledge_item = models.OneToOneField(
        "KnowledgeItem", on_delete=models.CASCADE, related_name="quiz", null=True, blank=True
    )
    titre = models.CharField(max_length=140, default="Quiz")
    seuil_reussite_pct = models.PositiveSmallIntegerField(
        default=70,
        help_text="Pourcentage minimum pour valider le quiz (ex: 70).",
    )

    class Meta:
        ordering = ["module__ordre"]
        verbose_name_plural = "Quiz"

    def __str__(self) -> str:
        return self.titre or (self.module.titre if self.module else "Quiz")


class QuizQuestion(models.Model):
    """Question d'un quiz (choix multiples)."""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    enonce = models.CharField(max_length=500)
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["quiz", "ordre"]

    def __str__(self) -> str:
        return self.enonce[:60] + ("…" if len(self.enonce) > 60 else "")


class QuizChoice(models.Model):
    """Réponse possible à une question (une seule correcte par question)."""
    question = models.ForeignKey(
        QuizQuestion, on_delete=models.CASCADE, related_name="choices"
    )
    texte = models.CharField(max_length=300)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["question", "id"]

    def __str__(self) -> str:
        return self.texte[:50] + ("…" if len(self.texte) > 50 else "")


class UserQuizAttempt(models.Model):
    """Tentative d'un utilisateur à un quiz (score et statut)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts"
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score_pct = models.PositiveSmallIntegerField(default=0)
    passed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
        unique_together = [["user", "quiz"]]

    def __str__(self) -> str:
        return f"{self.user} — {self.quiz} ({self.score_pct}%)"


class KnowledgeKind(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class KnowledgeItem(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        IN_REVIEW = "in_review", "En validation"
        PUBLISHED = "published", "Publié"
        REJECTED = "rejected", "Rejeté"
        ARCHIVED = "archived", "Archivé"

    title = models.CharField(max_length=180)
    description = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="Résumé court de la connaissance (une phrase).",
    )
    kind = models.ForeignKey(KnowledgeKind, on_delete=models.PROTECT, related_name="knowledge_items")
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="knowledge_items",
        default=None,
        null=True,
        blank=True,
    )
    author = models.CharField(max_length=120, blank=True, default="")
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_knowledge_items",
    )
    content = models.TextField()
    video_url = models.URLField(blank=True, default="")
    attachment = models.FileField(upload_to="knowledge_attachments/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    tags = models.ManyToManyField("Tag", blank=True, related_name="knowledge_items")
    competences = models.ManyToManyField(Competence, blank=True, related_name="knowledge_items")
    numero_version = models.CharField(max_length=40, default="1.0", help_text="Ex: 1.0, 2024, v2")
    rejection_comment = models.TextField(blank=True, default="", help_text="Commentaire du manager en cas de rejet")
    read_time_min = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    def get_current_version(self):
        """Retourne la version marquée comme actuelle, ou la plus récente."""
        current = self.versions.filter(est_actuelle=True).first()
        if current:
            return current
        return self.versions.order_by("-date_creation").first()

    def get_display_author(self):
        """Auteur affiché : profil/user ou champ author."""
        if self.author_user_id:
            profile = getattr(self.author_user, "profile", None)
            if profile:
                return profile.display_name
            return self.author_user.get_full_name() or self.author_user.get_username()
        return self.author or "—"


class KnowledgeVersion(models.Model):
    """Version d'une connaissance (historique, numéro, contenu, auteur)."""
    knowledge_item = models.ForeignKey(
        KnowledgeItem, on_delete=models.CASCADE, related_name="versions"
    )
    numero_version = models.CharField(max_length=40)
    content = models.TextField(blank=True, default="")
    author_name = models.CharField(max_length=120, blank=True, default="")
    date_creation = models.DateTimeField(auto_now_add=True)
    est_actuelle = models.BooleanField(default=False)
    note_modification = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-date_creation"]
        unique_together = [["knowledge_item", "numero_version"]]

    def __str__(self) -> str:
        return f"{self.knowledge_item.title} — v{self.numero_version}"


class ModuleKnowledgeItem(models.Model):
    """Lien module <-> connaissance avec ordre."""
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="knowledge_links")
    knowledge_item = models.ForeignKey(
        KnowledgeItem, on_delete=models.CASCADE, related_name="module_links"
    )
    ordre = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["module", "ordre"]


class Progression(models.Model):
    """Suivi individuel d'un plan d'intégration (employé, plan, %)."""
    class StatutProgression(models.TextChoices):
        EN_COURS = "en_cours", "En cours"
        TERMINE = "termine", "Terminé"
        CERTIFIE = "certifie", "Certifié"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progressions")
    plan = models.ForeignKey(
        PlanIntegration, on_delete=models.CASCADE, related_name="progressions"
    )
    pourcentage = models.PositiveSmallIntegerField(default=0)
    statut = models.CharField(
        max_length=20, choices=StatutProgression.choices, default=StatutProgression.EN_COURS
    )
    date_fin = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = [["user", "plan"]]
        ordering = ["-date_fin"]


class UserProfile(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        EMPLOYEE = "employee", "Employé"
        MANAGER = "manager", "Manager"
        NEW_EMPLOYEE = "new_employee", "Nouveau"

    class TypeContrat(models.TextChoices):
        CDI = "cdi", "CDI"
        CDD = "cdd", "CDD"
        STAGE = "stage", "Stage"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", null=True, blank=True)
    display_name = models.CharField(max_length=120, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles")
    poste = models.ForeignKey(
        "Poste", on_delete=models.SET_NULL, null=True, blank=True, related_name="profiles"
    )
    type_contrat = models.CharField(
        max_length=20, choices=TypeContrat.choices, blank=True, default=""
    )
    date_embauche = models.DateField(blank=True, null=True)
    must_change_password = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(upload_to="profiles/", blank=True, null=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name


class OnboardingStep(models.Model):
    title = models.CharField(max_length=140)
    description = models.CharField(max_length=240, blank=True, default="")
    order = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.title




class Tag(models.Model):
    name = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name
