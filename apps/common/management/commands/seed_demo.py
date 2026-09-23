"""Create a demo business with shops, reps and a few weeks of ledger history.

    python manage.py seed_demo
Then log in with phone 01711-000111 (the OTP is printed / returned in dev).
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business, Membership, Role
from apps.ledger.models import EntryType
from apps.ledger.services import post_entry
from apps.notifications.models import ReminderRule
from apps.shops.models import Area, Shop

REPS = [("Rafiq Hasan", "01712445566", ["Mirpur-10", "Kazipara"]),
        ("Sumon Mia", "01819223344", ["Farmgate", "Mohammadpur"]),
        ("Jahid Islam", "01911778899", ["Uttara"])]
SHOPS = [
    ("Rahman Store", "Abdur Rahman", "01711234567", "Mirpur-10", 80000, 15),
    ("Karim Traders", "Karim Uddin", "01819556677", "Kazipara", 50000, 15),
    ("Bismillah General Store", "Nur Hossain", "01913112233", "Farmgate", 60000, 20),
    ("Mayer Doa Store", "Selim Reza", "01715667788", "Mohammadpur", 40000, 15),
    ("Nabil Enterprise", "Nabil Ahmed", "01552889900", "Uttara", 120000, 30),
    ("Shapla Pharmacy", "Dr. Shahana", "01671334455", "Mirpur-10", 70000, 30),
    ("Hasan Hardware", "Mehedi Hasan", "01799221100", "Kazipara", 90000, 20),
    ("Al-Madina Store", "Faruk Mollah", "01817909090", "Farmgate", 45000, 15),
    ("Rupali Traders", "Rupa Akter", "01912454545", "Uttara", 55000, 15),
    ("Molla Brothers", "Jamal Molla", "01716343434", "Mohammadpur", 65000, 20),
    ("Tania Cosmetics", "Tania Sultana", "01611787878", "Mirpur-10", 30000, 15),
    ("Shonali Bazar", "Habib Khan", "01818121212", "Uttara", 75000, 20),
]


LATE_PAYERS = {"Karim Traders", "Hasan Hardware", "Molla Brothers", "Mayer Doa Store"}


class Command(BaseCommand):
    help = "Seed a demo business (Karim & Sons Distribution) with realistic data."

    @transaction.atomic
    def handle(self, *args, **opts):
        rnd = random.Random(7)
        today = timezone.localdate()
        owner, _ = User.objects.get_or_create(phone="+8801711000111", defaults={"name": "Karim Chowdhury"})
        if Business.objects.filter(owner=owner, name="Karim & Sons Distribution").exists():
            self.stdout.write(self.style.WARNING("Demo business already exists."))
            return
        biz = Business.objects.create(owner=owner, name="Karim & Sons Distribution", trade_type="fmcg",
                                      address="42 Moulvibazar Road, Old Dhaka", phone="+8801711000111", plan="pro")
        Membership.objects.create(business=biz, user=owner, role=Role.OWNER)
        manager, _ = User.objects.get_or_create(phone="+8801819000222", defaults={"name": "Nasrin Akter"})
        Membership.objects.create(business=biz, user=manager, role=Role.MANAGER)
        ReminderRule.objects.create(business=biz)

        areas = {}
        for name, phone, area_names in REPS:
            rep, _ = User.objects.get_or_create(phone="+88" + phone, defaults={"name": name})
            Membership.objects.create(business=biz, user=rep, role=Role.REP, invited_by=owner)
            for a in area_names:
                areas[a] = Area.objects.create(business=biz, name=a, assigned_rep=rep)

        for name, owner_name, phone, area, limit, due_days in SHOPS:
            shop = Shop.objects.create(business=biz, name=name, owner_name=owner_name, phone="+88" + phone,
                                       area=areas[area], credit_limit=limit, due_days=due_days,
                                       address=f"{area}, Dhaka")
            rep = areas[area].assigned_rep
            post_entry(shop=shop, entry_type=EntryType.OPENING, amount=Decimal(round(limit * rnd.uniform(.1, .25), -2)),
                       user=owner, entry_date=today - timedelta(days=70), allow_over_limit=True, note="Opening balance")
            day, memo = 60, 2200
            while day > 0:
                memo += 1
                post_entry(shop=shop, entry_type=EntryType.SALE, amount=Decimal(round(limit * rnd.uniform(.08, .2), -2)),
                           user=rep, entry_date=today - timedelta(days=day), memo_no=f"M-{memo}", allow_over_limit=True)
                day -= rnd.randint(6, 14)
                if day > 0 and rnd.random() > (.6 if name in LATE_PAYERS else .1):
                    post_entry(shop=shop, entry_type=EntryType.PAYMENT, amount=Decimal(round(limit * rnd.uniform(.1, .2), -2)),
                               user=rep, entry_date=today - timedelta(days=day), method=rnd.choice(["cash", "bkash", "nagad"]))
        self.stdout.write(self.style.SUCCESS(f"Created '{biz.name}' ({biz.alias}) with {len(SHOPS)} shops. Owner login: 01711-000111"))
