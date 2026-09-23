import logging
import os
import pprint
import uuid

from autoslug import AutoSlugField
from django.conf import settings
from django.db import models
from easy_thumbnails.fields import ThumbnailerImageField

logger = logging.getLogger(__name__)
USER_IP_ADDRESS = ""
User = settings.AUTH_USER_MODEL


def media_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"documents/{uuid.uuid4().hex}{ext}"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AliasModel(TimeStampedModel):
    alias = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True


class CreatedAtUpdatedAtBaseModel(models.Model):
    alias = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set",
        verbose_name="Created By",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set",
        verbose_name="Updated By",
    )
    user_ip = models.GenericIPAddressField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True
        ordering = ("-created_at",)

    def _print(self):
        _pp = pprint.PrettyPrinter(indent=4)
        _pp.pprint("------------------------------------------")
        logger.info("Details of %s:", self)
        _pp.pprint(vars(self))
        _pp.pprint("------------------------------------------")

    def save(self, *args, **kwargs):
        self.full_clean()
        self.user_ip = USER_IP_ADDRESS or None
        super().save(*args, **kwargs)


class NameSlugDescriptionBaseModel(CreatedAtUpdatedAtBaseModel):
    name = models.CharField(max_length=200, db_index=True)
    slug = AutoSlugField(populate_from="name", always_update=True, unique=True, allow_unicode=True)
    description = models.TextField(blank=True)

    class Meta:
        abstract = True
        ordering = ("name",)

    def __str__(self):
        return self.get_name()

    def get_name(self):
        return f"ID: {self.id}, Name: {self.name}, Slug: {self.slug}"


class TimestampThumbnailImageField(ThumbnailerImageField):
    def generate_filename(self, instance, filename):
        new_filename = f"{uuid.uuid4().hex}_{filename}"
        return super().generate_filename(instance, new_filename)


class DocumentFile(CreatedAtUpdatedAtBaseModel):
    file = models.FileField(upload_to=media_path)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return os.path.basename(self.file.name)