from apps.businesses.models import Business, Membership, Role
from apps.shops.models import Shop
from conftest import url


def test_outsider_gets_404(setup, make_user, client_for):
    outsider = make_user("+8801999999999", "Stranger")
    other_biz = Business.objects.create(owner=outsider, name="Other Co")
    Membership.objects.create(business=other_biz, user=outsider, role=Role.OWNER)
    c = client_for(outsider)
    assert c.get(url(setup["biz"], "shops/")).status_code == 404
    assert c.get(url(setup["biz"], f"shops/{setup['shop'].alias}/")).status_code == 404
    assert c.get(url(setup["biz"], "dashboard/")).status_code == 404
    # and their own business can't be used to reach our shop either
    assert c.get(url(other_biz, f"shops/{setup['shop'].alias}/")).status_code == 404


def test_rep_sees_only_assigned_area(setup, client_for):
    c = client_for(setup["rep"])
    names = [s["name"] for s in c.get(url(setup["biz"], "shops/")).data["results"]]
    assert names == ["Rahman Store"]
    assert c.get(url(setup["biz"], f"shops/{setup['other'].alias}/")).status_code == 404


def test_rep_cannot_create_shop(setup, client_for):
    r = client_for(setup["rep"]).post(url(setup["biz"], "shops/"), {"name": "New"}, format="json")
    assert r.status_code == 403


def test_owner_creates_shop_with_opening_balance(setup, client_for):
    r = client_for(setup["owner"]).post(
        url(setup["biz"], "shops/"),
        {"name": "Tania Cosmetics", "phone": "01611-787878", "opening_balance": "12000"}, format="json",
    )
    assert r.status_code == 201, r.data
    shop = Shop.objects.get(alias=r.data["alias"])
    assert shop.current_balance == 12000 and shop.phone == "+8801611787878"


def test_create_business_makes_me_owner(make_user, client_for):
    u = make_user("+8801711111111")
    r = client_for(u).post("/api/v1/businesses/", {"name": "My Distribution"}, format="json")
    assert r.status_code == 201
    assert r.data["my_role"] == "owner"


def test_invite_member(setup, client_for):
    r = client_for(setup["owner"]).post(url(setup["biz"], "members/"),
                                        {"phone": "01555123456", "name": "New Rep", "role": "rep"}, format="json")
    assert r.status_code == 201, r.data
    assert r.data["role"] == "rep"


def test_shop_status_filters(setup, client_for):
    from datetime import timedelta

    from django.utils import timezone

    from apps.ledger.models import EntryType
    from apps.ledger.services import post_entry

    owner, shop, other = setup["owner"], setup["shop"], setup["other"]
    post_entry(shop=shop, entry_type=EntryType.SALE, amount=1000, user=owner,
               entry_date=timezone.localdate() - timedelta(days=40))  # overdue (due_days 15)
    post_entry(shop=other, entry_type=EntryType.SALE, amount=1000, user=owner)  # fresh
    c = client_for(owner)
    names = lambda q: [s["name"] for s in c.get(url(setup["biz"], f"shops/?status={q}")).data["results"]]
    assert names("overdue") == ["Rahman Store"]
    assert names("good") == ["Nabil Enterprise"]
