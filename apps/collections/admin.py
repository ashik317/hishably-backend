from django.contrib import admin

from .models import CashHandover, CollectionVisit

admin.site.register(CollectionVisit)
admin.site.register(CashHandover)
