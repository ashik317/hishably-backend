from django.db import models
from django.utils.translation import gettext_lazy as _


class NameTitleChoices(models.TextChoices):
    MR = "MR", _("Mr.")
    MRS = "MRS", _("Mrs.")
    MS = "MS", _("Ms.")
    MISS = "MISS", _("Miss")
    DR = "DR", _("Dr.")
    PROFESSOR = "PROFESSOR", _("Prof.")


class Language(models.TextChoices):
    BANGLA = "bn", _("Bangla")
    ENGLISH = "en", _("English")