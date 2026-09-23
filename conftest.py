import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.businesses.models import Business, Membership, Role
from apps.shops.models import Area, Shop


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    from django.core.cache import cache
    cache.clear()


@pytest.fixture
def make_user(db):
    def _make(phone, name="User"):
        return User.objects.create_user(phone=phone, name=name)
    return _make


@pytest.fixture
def client_for():
    def _client(user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
        return c
    return _client


@pytest.fixture
def setup(db, make_user):
    """Business with an owner, a rep (assigned to Mirpur), an accountant and two shops."""
    owner = make_user("+8801711000111", "Karim")
    rep = make_user("+8801712445566", "Rafiq")
    accountant = make_user("+8801678000333", "Anwar")
    biz = Business.objects.create(owner=owner, name="Karim & Sons")
    Membership.objects.create(business=biz, user=owner, role=Role.OWNER)
    Membership.objects.create(business=biz, user=rep, role=Role.REP)
    Membership.objects.create(business=biz, user=accountant, role=Role.ACCOUNTANT)
    mirpur = Area.objects.create(business=biz, name="Mirpur-10", assigned_rep=rep)
    uttara = Area.objects.create(business=biz, name="Uttara")
    shop = Shop.objects.create(business=biz, name="Rahman Store", owner_name="Abdur Rahman",
                               phone="+8801711234567", area=mirpur, credit_limit=50000, due_days=15)
    other = Shop.objects.create(business=biz, name="Nabil Enterprise", area=uttara, credit_limit=100000)
    return {"owner": owner, "rep": rep, "accountant": accountant, "biz": biz, "shop": shop, "other": other}


def url(biz, path):
    return f"/api/v1/b/{biz.alias}/{path}"
