"""Mini App ishlatadigan API oqimi: initData → JWT → hisobot → kelishuv.

initData haqiqiy HMAC imzosi bilan yasaladi — auth qatlami ham tekshiriladi.
"""

from __future__ import annotations

import json

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security import build_init_data
from app.db.base import Base
from app.db.models import Employee, Role, Submission, SubmissionStatus, Vehicle
from app.db.session import SessionFactory, engine
from app.seeds.loader import seed_all

MECHANIC_TG = 7101
ADMIN_TG = 7102
ACCOUNTANT_TG = 7103


@pytest.fixture
async def api():  # noqa: ANN201
    """Toza baza + ASGI klient (tarmoqsiz)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        await seed_all(session)
        roles = {
            role.code: role for role in (await session.execute(sa.select(Role))).scalars().all()
        }
        session.add_all(
            [
                Employee(
                    full_name="Karimov B.",
                    phone="+998901110001",
                    role_id=roles["mechanic"].id,
                    tg_user_id=MECHANIC_TG,
                ),
                Employee(
                    full_name="Admin A.",
                    phone="+998901110002",
                    role_id=roles["admin"].id,
                    tg_user_id=ADMIN_TG,
                ),
                Employee(
                    full_name="Buxgalter B.",
                    phone="+998901110003",
                    role_id=roles["accountant"].id,
                    tg_user_id=ACCOUNTANT_TG,
                ),
                Vehicle(
                    plate_number="01A123BC",
                    plate_display="01 A 123 BC",
                    brand="BYD",
                    model="Chazor",
                    year=2024,
                ),
            ]
        )
        await session.commit()

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def init_data_for(tg_user_id: int) -> str:
    import time

    return build_init_data(
        settings.bot_token,
        {
            "auth_date": int(time.time()),
            "query_id": "AAF",
            "user": {"id": tg_user_id, "first_name": "Test", "language_code": "uz"},
        },
    )


async def login(client: AsyncClient, tg_user_id: int) -> dict:
    response = await client.post(
        "/api/v1/auth/telegram", json={"init_data": init_data_for(tg_user_id)}
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- Auth --------------------------------------------------------------------


async def test_init_data_signature_is_verified(api):
    bad = "user=%7B%22id%22%3A7101%7D&auth_date=1&hash=deadbeef"
    response = await api.post("/api/v1/auth/telegram", json={"init_data": bad})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_init_data"


async def test_unknown_telegram_user_is_rejected(api):
    response = await api.post(
        "/api/v1/auth/telegram", json={"init_data": init_data_for(999999)}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_in_registry"


async def test_login_returns_role_and_templates(api):
    auth = await login(api, MECHANIC_TG)
    assert auth["employee"]["role"]["kind"] == "reporter"
    assert [tpl["code"] for tpl in auth["templates"]] == ["car_repair"]
    assert auth["access_token"] and auth["refresh_token"]


async def test_refresh_rotates_token(api):
    auth = await login(api, MECHANIC_TG)
    response = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["refresh_token"] != auth["refresh_token"]

    # eski token endi ishlamaydi (rotatsiya)
    again = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": auth["refresh_token"]}
    )
    assert again.status_code == 401


async def test_endpoints_require_token(api):
    response = await api.get("/api/v1/submissions")
    assert response.status_code == 401


# --- R3: tayanch narx yopiqligi ----------------------------------------------


async def test_reference_price_hidden_from_reporter(api):
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)

    as_mechanic = await api.get(
        "/api/v1/work-catalog?q=kolodka", headers=auth_header(mechanic["access_token"])
    )
    assert as_mechanic.status_code == 200
    assert all(item["reference_price"] is None for item in as_mechanic.json())

    as_admin = await api.get(
        "/api/v1/work-catalog?q=kolodka", headers=auth_header(admin["access_token"])
    )
    assert any(item["reference_price"] is not None for item in as_admin.json())


# --- To'liq oqim --------------------------------------------------------------


async def _upload_photo(api: AsyncClient, token: str, submission_id: int, field: str) -> int:
    payload = b"\xff\xd8\xff\xe0" + bytes(64) + field.encode()
    response = await api.post(
        "/api/v1/media/upload",
        headers=auth_header(token),
        data={
            "submission_id": str(submission_id),
            "field_code": field,
            "kind": "other",
            "source": "camera",
        },
        files={"file": ("photo.jpg", payload, "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _submit_repair(api: AsyncClient, m_token: str, *, price: int = 250000) -> int:
    """Yuborilgan ta'mir hisoboti yasaydi (testlar uchun qisqa yo'l)."""
    vehicle_id = (
        await api.get("/api/v1/vehicles/lookup?plate=01A123BC", headers=auth_header(m_token))
    ).json()["id"]
    submission_id = (
        await api.post(
            "/api/v1/submissions",
            headers=auth_header(m_token),
            json={"template_code": "car_repair"},
        )
    ).json()["id"]

    media_ids = {}
    for field in (
        "photo_car_before",
        "photo_problem",
        "photo_after",
        "photo_car_after",
    ):
        media_ids[field] = [await _upload_photo(api, m_token, submission_id, field)]

    await api.patch(
        f"/api/v1/submissions/{submission_id}",
        headers=auth_header(m_token),
        json={
            "data": {
                "plate": {"vehicle_id": vehicle_id, "plate": "01A123BC"},
                "category": "brakes",
                "problem_description": "Old tormoz kolodkasi yeyilgan",
                "comment": "Kolodka almashtirildi, disk normal",
                **media_ids,
            }
        },
    )
    await api.put(
        f"/api/v1/submissions/{submission_id}/lines",
        headers=auth_header(m_token),
        json={
            "lines": [
                {
                    "kind": "labor",
                    "name": "Old tormoz kolodkasini almashtirish",
                    "qty": 1,
                    "unit_price": price,
                }
            ]
        },
    )
    await api.post(
        f"/api/v1/submissions/{submission_id}/mark-left", headers=auth_header(m_token)
    )
    submitted = await api.post(
        f"/api/v1/submissions/{submission_id}/submit", headers=auth_header(m_token)
    )
    assert submitted.status_code == 200, submitted.text
    return submission_id


async def test_full_submission_flow(api):
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)
    m_token = mechanic["access_token"]
    a_token = admin["access_token"]

    # shablon sxemasi — Mini App form renderer shu bilan forma chizadi
    schema = await api.get("/api/v1/templates/car_repair", headers=auth_header(m_token))
    assert schema.status_code == 200
    fields = {f["code"] for f in schema.json()["data"]["fields"]}
    assert {"plate", "works", "photo_problem", "comment"} <= fields

    # mashina qidiruvi
    vehicle = await api.get(
        "/api/v1/vehicles/lookup?plate=01 A 123 BC", headers=auth_header(m_token)
    )
    assert vehicle.status_code == 200
    vehicle_id = vehicle.json()["id"]

    # qoralama — arrived_at server vaqti
    created = await api.post(
        "/api/v1/submissions",
        headers=auth_header(m_token),
        json={"template_code": "car_repair"},
    )
    assert created.status_code == 201, created.text
    submission = created.json()
    assert submission["arrived_at"] is not None
    submission_id = submission["id"]

    # fotolar
    media_ids = {}
    for field in (
        "photo_car_before",
        "photo_problem",
        "photo_after",
        "photo_car_after",
    ):
        media_ids[field] = [await _upload_photo(api, m_token, submission_id, field)]

    # maydonlar
    patched = await api.patch(
        f"/api/v1/submissions/{submission_id}",
        headers=auth_header(m_token),
        json={
            "data": {
                "plate": {"vehicle_id": vehicle_id, "plate": "01A123BC"},
                "category": "brakes",
                "problem_description": "Old tormoz kolodkasi yeyilgan",
                "comment": "Kolodka almashtirildi, disk normal",
                **media_ids,
            }
        },
    )
    assert patched.status_code == 200, patched.text

    # ish qatorlari — narxni muallif qo'yadi
    lines = await api.put(
        f"/api/v1/submissions/{submission_id}/lines",
        headers=auth_header(m_token),
        json={
            "lines": [
                {
                    "kind": "labor",
                    "name": "Old tormoz kolodkasini almashtirish",
                    "qty": 1,
                    "unit_price": 250000,
                }
            ]
        },
    )
    assert lines.status_code == 200, lines.text
    assert float(lines.json()["proposed_labor_amount"]) == 250000.0

    # left_at to'ldirilmagan — yuborib bo'lmaydi
    early = await api.post(
        f"/api/v1/submissions/{submission_id}/submit", headers=auth_header(m_token)
    )
    assert early.status_code == 400
    assert "_left_at" in early.json()["error"]["fields"]

    left = await api.post(
        f"/api/v1/submissions/{submission_id}/mark-left", headers=auth_header(m_token)
    )
    assert left.status_code == 200
    assert left.json()["left_at"] is not None

    submitted = await api.post(
        f"/api/v1/submissions/{submission_id}/submit", headers=auth_header(m_token)
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "submitted"

    # --- Admin: narx konteksti (R3 — ustaga yopiq) ---
    forbidden = await api.get(
        f"/api/v1/submissions/{submission_id}/price-context", headers=auth_header(m_token)
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "price_reference_hidden"

    context = await api.get(
        f"/api/v1/submissions/{submission_id}/price-context", headers=auth_header(a_token)
    )
    assert context.status_code == 200
    line_id = context.json()[0]["line_id"]

    # R2 — oshirib bo'lmaydi
    increase = await api.post(
        f"/api/v1/submissions/{submission_id}/propose-price",
        headers=auth_header(a_token),
        json={"lines": [{"line_id": line_id, "amount": 300000}], "comment": "qo'shimcha ish"},
    )
    assert increase.status_code == 422
    assert increase.json()["error"]["code"] == "price_increase_forbidden"

    # kamaytirish — sabab bilan
    proposed = await api.post(
        f"/api/v1/submissions/{submission_id}/propose-price",
        headers=auth_header(a_token),
        json={
            "lines": [{"line_id": line_id, "amount": 180000}],
            "comment": "Bu ish odatda 175 000 ga bo'lgan",
        },
    )
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["status"] == "price_negotiation"

    # usta rozi bo'ladi
    accepted = await api.post(
        f"/api/v1/submissions/{submission_id}/accept-price", headers=auth_header(m_token)
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "approved"
    assert float(accepted.json()["labor_amount"]) == 180000.0
    assert float(accepted.json()["proposed_labor_amount"]) == 250000.0  # R2a

    # kelishuv izi
    history = await api.get(
        f"/api/v1/submissions/{submission_id}/price-history", headers=auth_header(a_token)
    )
    decisions = [row["decision"] for row in history.json()]
    assert "price_proposed" in decisions and "price_accepted" in decisions

    # dashboard: tejamkorlik
    board = await api.get("/api/v1/reports/dashboard", headers=auth_header(a_token))
    assert float(board.json()["saved"]) == 70000.0

    # ustaning o'z statistikasi
    stats = await api.get("/api/v1/me/price-stats", headers=auth_header(m_token))
    assert stats.json()["lines_reduced"] == 1


async def test_reporter_cannot_see_others_submission(api):
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)

    created = await api.post(
        "/api/v1/submissions",
        headers=auth_header(admin["access_token"]),
        json={"template_code": "car_repair"},
    )
    submission_id = created.json()["id"]

    response = await api.get(
        f"/api/v1/submissions/{submission_id}", headers=auth_header(mechanic["access_token"])
    )
    assert response.status_code == 403


async def test_accountant_cannot_approve(api):
    mechanic = await login(api, MECHANIC_TG)
    accountant = await login(api, ACCOUNTANT_TG)

    created = await api.post(
        "/api/v1/submissions",
        headers=auth_header(mechanic["access_token"]),
        json={"template_code": "car_repair"},
    )
    submission_id = created.json()["id"]
    async with SessionFactory() as session:
        submission = await session.get(Submission, submission_id)
        submission.status = SubmissionStatus.SUBMITTED
        await session.commit()

    response = await api.post(
        f"/api/v1/submissions/{submission_id}/approve",
        headers=auth_header(accountant["access_token"]),
        json={},
    )
    assert response.status_code == 403


async def test_language_can_be_changed(api):
    auth = await login(api, MECHANIC_TG)
    response = await api.patch(
        "/api/v1/me", headers=auth_header(auth["access_token"]), json={"lang": "ru"}
    )
    assert response.status_code == 200
    assert response.json()["lang"] == "ru"


async def test_catalog_items_for_select_fields(api):
    auth = await login(api, MECHANIC_TG)
    response = await api.get(
        "/api/v1/catalog-items?catalog=fault_categories",
        headers=auth_header(auth["access_token"]),
    )
    assert response.status_code == 200
    codes = {row["code"] for row in response.json()["data"]}
    assert {"brakes", "tyres", "battery"} <= codes


async def test_openapi_is_served(api):
    response = await api.get("/openapi.json")
    assert response.status_code == 200
    spec = json.loads(response.text)
    assert "/api/v1/submissions/{submission_id}/propose-price" in spec["paths"]


# --- Javob shakli (Mini App klienti shunga tayanadi) --------------------------


async def test_submission_response_is_not_an_envelope(api):
    """Regressiya: hisobot obyektida `data` maydoni bor — u konvert EMAS.

    Mini App `{data, meta}` konvertini ochadi; agar hisobot ham konvert deb
    o'qilsa, `id` yo'qoladi va klient `/submissions/undefined` so'raydi (422).
    """
    auth = await login(api, MECHANIC_TG)
    response = await api.post(
        "/api/v1/submissions",
        headers=auth_header(auth["access_token"]),
        json={"template_code": "car_repair"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert set(payload) != {"data"}, "hisobot konvertga o'ralmasligi kerak"
    assert isinstance(payload["id"], int)
    assert isinstance(payload["data"], dict)  # forma qiymatlari — konvert emas


async def test_wrapped_endpoints_use_data_envelope(api):
    """Konvert ishlatadigan endpointlar: `{data: ...}` va boshqa kalitsiz."""
    auth = await login(api, MECHANIC_TG)
    headers = auth_header(auth["access_token"])

    for path in ("/api/v1/templates/car_repair", "/api/v1/catalog-items?catalog=fault_categories"):
        payload = (await api.get(path, headers=headers)).json()
        assert set(payload) <= {"data", "meta"}, path
        assert "data" in payload, path


async def test_patch_moves_vehicle_into_service(api):
    """Mini App qoralamani `vehicle_id`siz ochadi — mashina PATCH'da tanlanadi."""
    auth = await login(api, MECHANIC_TG)
    headers = auth_header(auth["access_token"])

    vehicle = (await api.get("/api/v1/vehicles/lookup?plate=01A123BC", headers=headers)).json()
    assert vehicle["status"] == "active"

    created = await api.post(
        "/api/v1/submissions", headers=headers, json={"template_code": "car_repair"}
    )
    submission_id = created.json()["id"]

    patched = await api.patch(
        f"/api/v1/submissions/{submission_id}",
        headers=headers,
        json={"data": {"plate": {"vehicle_id": vehicle["id"], "plate": "01A123BC"}}},
    )
    assert patched.status_code == 200
    assert patched.json()["vehicle"]["status"] == "in_service"


async def test_media_upload_rejects_path_traversal(api):
    """`field_code` yo'lga kiradi — `../` bilan chiqib ketishga urinish rad etiladi."""
    auth = await login(api, MECHANIC_TG)
    headers = auth_header(auth["access_token"])
    created = await api.post(
        "/api/v1/submissions", headers=headers, json={"template_code": "car_repair"}
    )
    submission_id = created.json()["id"]

    response = await api.post(
        "/api/v1/media/upload",
        headers=headers,
        data={
            "submission_id": str(submission_id),
            "field_code": "../../../../tmp/evil",
            "kind": "other",
            "source": "camera",
        },
        files={"file": ("x.jpg", b"\xff\xd8\xff\xe0" + bytes(32), "image/jpeg")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["fields"]["field_code"] == "invalid_field_code"


# --- Konstruktorlar (Faza 2) --------------------------------------------------


def wash_payload(**overrides) -> dict:
    payload = {
        "code": "car_wash",
        "name": {"uz": "Yuvish hisoboti", "ru": "Отчёт о мойке"},
        "icon": "🧼",
        "subject_type": "vehicle",
        "field_mapping": {"vehicle": "plate"},
        "sections": [{"code": "main", "title": {"uz": "Yuvish"}}],
        "fields": [
            {
                "code": "plate",
                "section": "main",
                "label": {"uz": "Mashina raqami"},
                "type": "vehicle_picker",
                "required": True,
            },
            {
                "code": "works",
                "section": "main",
                "label": {"uz": "Bajarilgan ishlar"},
                "type": "lines",
                "required": True,
                "options": {"kind": "labor"},
            },
        ],
    }
    payload.update(overrides)
    return payload


async def test_template_constructor_is_admin_only(api):
    auth = await login(api, MECHANIC_TG)
    headers = auth_header(auth["access_token"])

    assert (await api.get("/api/v1/admin/templates", headers=headers)).status_code == 403
    response = await api.post("/api/v1/admin/templates", headers=headers, json=wash_payload())
    assert response.status_code == 403


async def test_template_draft_publish_edit_cycle(api):
    """Yaratish → nashr → tahrir → qayta nashr. Har qadamda holat aniq."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])

    created = await api.post("/api/v1/admin/templates", headers=admin, json=wash_payload())
    assert created.status_code == 201, created.text
    template = created.json()["data"]
    assert template["is_draft"] is True and template["published_version"] is None

    published = await api.post(
        f"/api/v1/admin/templates/{template['id']}/publish", headers=admin
    )
    assert published.status_code == 200
    assert published.json()["data"] == {**published.json()["data"], "is_draft": False}
    assert published.json()["data"]["published_version"] == 1

    # ikkinchi nashr — o'zgarishsiz mumkin emas
    again = await api.post(f"/api/v1/admin/templates/{template['id']}/publish", headers=admin)
    assert again.status_code == 422

    edited = await api.patch(
        f"/api/v1/admin/templates/{template['id']}",
        headers=admin,
        json=wash_payload(icon="🚿"),
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["version"] == 2
    assert edited.json()["data"]["is_draft"] is True
    assert edited.json()["data"]["published_version"] == 1


async def test_template_validation_errors_are_reported_per_field(api):
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    broken = wash_payload()
    broken["fields"][0]["type"] = "signature"

    response = await api.post("/api/v1/admin/templates", headers=admin, json=broken)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"]["fields.0.type"] == "unsupported_type"


async def test_new_role_sees_new_template_after_publish(api):
    """Faza 2 chiqish mezoni: yangi rol + shablon → xodim menyusida paydo bo'ladi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])

    created = await api.post("/api/v1/admin/templates", headers=admin, json=wash_payload())
    template_id = created.json()["data"]["id"]

    role = await api.post(
        "/api/v1/admin/roles",
        headers=admin,
        json={
            "code": "washer",
            "name_uz": "Yuvuvchi",
            "name_ru": "Мойщик",
            "icon": "🧼",
            "kind": "reporter",
            "template_ids": [template_id],
        },
    )
    assert role.status_code == 201, role.text
    role_id = role.json()["data"]["id"]

    # ustani yangi rolga o'tkazamiz
    employees = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    mechanic_id = next(e["id"] for e in employees if e["phone"] == "+998901110001")
    moved = await api.post(
        f"/api/v1/admin/employees/{mechanic_id}/role", headers=admin, json={"role_id": role_id}
    )
    assert moved.status_code == 200

    # nashr etilmagan — menyu bo'sh
    mechanic = auth_header((await login(api, MECHANIC_TG))["access_token"])
    assert (await api.get("/api/v1/templates", headers=mechanic)).json() == []

    pub = await api.post(f"/api/v1/admin/templates/{template_id}/publish", headers=admin)
    assert pub.status_code == 200, pub.text

    after = await login(api, MECHANIC_TG)
    assert [t["code"] for t in after["templates"]] == ["car_wash"]
    assert after["employee"]["role"]["name"] == "Yuvuvchi"


async def test_role_can_be_renamed_and_retemplated(api):
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    roles = (await api.get("/api/v1/admin/roles", headers=admin)).json()["data"]
    mechanic = next(r for r in roles if r["code"] == "mechanic")

    response = await api.patch(
        f"/api/v1/admin/roles/{mechanic['id']}",
        headers=admin,
        json={"name_uz": "Bosh usta", "icon": "🛠", "template_ids": []},
    )
    assert response.status_code == 200

    auth = await login(api, MECHANIC_TG)
    assert auth["employee"]["role"]["name"] == "Bosh usta"
    assert auth["templates"] == []


async def test_system_role_kind_is_locked(api):
    """Seed rollari (`is_system`) — turi o'zgarmaydi, nomi o'zgaradi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    roles = (await api.get("/api/v1/admin/roles", headers=admin)).json()["data"]
    admin_role = next(r for r in roles if r["code"] == "admin")

    response = await api.patch(
        f"/api/v1/admin/roles/{admin_role['id']}", headers=admin, json={"kind": "reporter"}
    )
    assert response.status_code == 422


async def test_last_admin_role_kind_change_is_blocked(api):
    """R8 — admin qolmasa, rolning turini o'zgartirib bo'lmaydi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])

    # adminni tizim bo'lmagan yangi admin rolga ko'chiramiz
    created = await api.post(
        "/api/v1/admin/roles",
        headers=admin,
        json={
            "code": "director",
            "name_uz": "Direktor",
            "name_ru": "Директор",
            "kind": "admin",
            "template_ids": [],
        },
    )
    director_id = created.json()["data"]["id"]

    employees = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    admin_id = next(e["id"] for e in employees if e["phone"] == "+998901110002")
    moved = await api.post(
        f"/api/v1/admin/employees/{admin_id}/role",
        headers=admin,
        json={"role_id": director_id},
    )
    assert moved.status_code == 200

    # endi yagona faol admin — shu rol. Turini o'zgartirish R8 ni buzadi.
    response = await api.patch(
        f"/api/v1/admin/roles/{director_id}", headers=admin, json={"kind": "reporter"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin_required"


# --- Xodim boshqaruvi (admin) -------------------------------------------------


async def test_employee_list_shows_link_status(api):
    """Admin ro'yxatda kim botga bog'langanini ko'radi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    rows = (await api.get("/api/v1/admin/employees", headers=admin)).json()

    by_phone = {row["phone"]: row for row in rows}
    assert by_phone["+998901110001"]["tg_linked"] is True  # login qilgan
    assert by_phone["+998901110001"]["status"] == "active"
    assert by_phone["+998901110001"]["role"]["code"] == "mechanic"
    assert by_phone["+998901110001"]["role_id"] > 0


async def test_admin_adds_employee_to_registry(api):
    """⭐ 1-qadam: admin reyestrga kiritadi. Telefon normalizatsiya qilinadi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    roles = (await api.get("/api/v1/admin/roles", headers=admin)).json()["data"]
    mechanic_role = next(r for r in roles if r["code"] == "mechanic")

    created = await api.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={
            "full_name": "Yangi Usta",
            "phone": "901119999",  # normalizatsiya sinovi
            "role_id": mechanic_role["id"],
            "workshop_name": "Chilonzor ustaxonasi",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["phone"] == "+998901119999"
    assert body["tg_linked"] is False  # hali botga kirmagan
    assert body["status"] == "active"

    rows = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    added = next(e for e in rows if e["phone"] == "+998901119999")
    assert added["workshop_name"] == "Chilonzor ustaxonasi"


async def test_new_employee_cannot_enter_miniapp_before_bot_binding(api):
    """⭐ 2-qadam **botda** bo'ladi: Mini App faqat `tg_user_id` bo'yicha kiritadi.

    Telefon raqamini Mini App ko'rmaydi — bog'lanish `/start` → `request_contact`
    orqali botda amalga oshadi (`test_bot_flow` da qoplangan). Shuning uchun
    reyestrga kiritilgan, lekin hali botga kirmagan xodim uchun Mini App
    `not_in_registry` qaytaradi — bu xato emas, model shunday.
    """
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    roles = (await api.get("/api/v1/admin/roles", headers=admin)).json()["data"]
    role_id = next(r for r in roles if r["code"] == "mechanic")["id"]

    await api.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={"full_name": "Yangi Usta", "phone": "+998901119999", "role_id": role_id},
    )

    denied = await api.post(
        "/api/v1/auth/telegram", json={"init_data": init_data_for(7199)}
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "not_in_registry"


async def test_duplicate_phone_is_rejected(api):
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    roles = (await api.get("/api/v1/admin/roles", headers=admin)).json()["data"]
    role_id = next(r for r in roles if r["code"] == "mechanic")["id"]

    response = await api.post(
        "/api/v1/admin/employees",
        headers=admin,
        json={"full_name": "Takror", "phone": "+998901110001", "role_id": role_id},
    )
    assert response.status_code == 422


async def test_employee_add_is_admin_only(api):
    mechanic = auth_header((await login(api, MECHANIC_TG))["access_token"])
    assert (await api.get("/api/v1/admin/employees", headers=mechanic)).status_code == 403
    response = await api.post(
        "/api/v1/admin/employees",
        headers=mechanic,
        json={"full_name": "X", "phone": "+998900000000", "role_id": 1},
    )
    assert response.status_code == 403


async def test_fired_employee_cannot_log_in_but_data_stays(api):
    """R5 — kirish bloklanadi, ma'lumot qoladi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    employees = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    mechanic_id = next(e["id"] for e in employees if e["phone"] == "+998901110001")

    response = await api.post(
        f"/api/v1/admin/employees/{mechanic_id}/status",
        headers=admin,
        json={"status": "fired"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "fired"

    denied = await api.post(
        "/api/v1/auth/telegram", json={"init_data": init_data_for(MECHANIC_TG)}
    )
    assert denied.status_code == 403

    # yozuvi reyestrda qoladi
    still = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    assert any(e["id"] == mechanic_id for e in still)


async def test_invalid_status_is_rejected(api):
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    employees = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    mechanic_id = next(e["id"] for e in employees if e["phone"] == "+998901110001")

    response = await api.post(
        f"/api/v1/admin/employees/{mechanic_id}/status",
        headers=admin,
        json={"status": "vacation"},
    )
    assert response.status_code == 422


async def test_last_admin_cannot_be_fired(api):
    """R8 — oxirgi adminni bo'shatib bo'lmaydi."""
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    employees = (await api.get("/api/v1/admin/employees", headers=admin)).json()
    admin_id = next(e["id"] for e in employees if e["phone"] == "+998901110002")

    response = await api.post(
        f"/api/v1/admin/employees/{admin_id}/status",
        headers=admin,
        json={"status": "fired"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_admin_required"


# --- Bildirishnoma matni va ro'yxat mosligi (2026-08-01 dagi xatolar) ---------


async def test_price_proposed_notification_has_no_raw_placeholders(api):
    """⚠️ Ustaga `{number} · {vehicle}` ko'rinishida xom shablon ketgan edi.

    Sabab: `t()` bitta yetishmagan kalitda (`vehicle`) BUTUN shablonni xom
    qaytarardi. Endi yetishmagan joy «—» bo'ladi, qolgani o'rniga qo'yiladi.
    """
    from app.bot import notifier
    from app.db.models import Notification, NotificationStatus
    from app.db.session import SessionFactory

    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)
    submission_id = await _submit_repair(api, mechanic["access_token"])

    proposed = await api.post(
        f"/api/v1/submissions/{submission_id}/propose-price",
        headers=auth_header(admin["access_token"]),
        json={
            "lines": [
                {
                    "line_id": (
                        await api.get(
                            f"/api/v1/submissions/{submission_id}",
                            headers=auth_header(admin["access_token"]),
                        )
                    ).json()["lines"][0]["id"],
                    "amount": 200000,
                }
            ],
            "comment": "Kolodka narxi bozorda arzonroq",
        },
    )
    assert proposed.status_code == 200, proposed.text

    async with SessionFactory() as session:
        row = (
            await session.execute(
                sa.select(Notification).where(
                    Notification.template_code == "notify_price_proposed",
                    Notification.status == NotificationStatus.pending,
                )
            )
        ).scalars().first()
        assert row is not None
        employee = await session.get(Employee, row.employee_id)
        text, _ = await notifier.render(session, row, employee)

    assert "{" not in text and "}" not in text, text
    assert "200 000" in text and "250 000" in text
    assert "01 A 123 BC" in text
    assert "Kolodka narxi bozorda arzonroq" in text


async def test_pending_list_keeps_reports_being_reviewed(api):
    """Admin ochgan hisobot (`in_review`) ro'yxatdan yo'qolib qolmasin.

    Dashboard plitkasi `submitted + in_review` sanaydi — ro'yxat ham shunday
    bo'lishi kerak, aks holda «1 ta kutmoqda», lekin ro'yxat bo'sh chiqadi.
    """
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)
    a_token = admin["access_token"]
    submission_id = await _submit_repair(api, mechanic["access_token"])

    # admin kartochkani ochadi → IN_REVIEW
    opened = await api.get(
        f"/api/v1/submissions/{submission_id}/price-context", headers=auth_header(a_token)
    )
    assert opened.status_code == 200
    await api.post(
        f"/api/v1/submissions/{submission_id}/reopen",
        headers=auth_header(a_token),
        json={"comment": "Muammo fotosi aniq emas"},
    )
    board = (await api.get("/api/v1/reports/dashboard", headers=auth_header(a_token))).json()

    listed = await api.get(
        "/api/v1/submissions?status=submitted,in_review,price_disputed",
        headers=auth_header(a_token),
    )
    assert listed.status_code == 200
    # reopen'dan keyin ikkalasi ham nolga tushadi — mos kelishi muhim
    assert len(listed.json()) == board["pending_review"]


async def test_status_filter_accepts_multiple_values(api):
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    mechanic = await login(api, MECHANIC_TG)
    await _submit_repair(api, mechanic["access_token"])

    one = await api.get("/api/v1/submissions?status=submitted", headers=admin)
    many = await api.get(
        "/api/v1/submissions?status=submitted,approved,paid", headers=admin
    )
    assert one.status_code == 200 and many.status_code == 200
    assert len(many.json()) >= len(one.json()) == 1


# --- Hisobotlar arxivi (admin «avvalgi hisobotlarni» ko'ra olsin) -------------


async def test_admin_sees_approved_reports_in_archive(api):
    """⚠️ Tasdiqlangach hisobot admin ko'zidan yo'qolib qolgan edi.

    Bosh ekranda faqat navbat va o'z hisobotlaring ko'rinadi — arxiv uchun
    filtrsiz (yoki `approved,paid`) ro'yxat kerak.
    """
    mechanic = await login(api, MECHANIC_TG)
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    submission_id = await _submit_repair(api, mechanic["access_token"])

    approved = await api.post(
        f"/api/v1/submissions/{submission_id}/approve", headers=admin, json={}
    )
    assert approved.status_code == 200

    # navbatda endi yo'q
    queue = await api.get(
        "/api/v1/submissions?status=submitted,in_review,price_disputed", headers=admin
    )
    assert [s["id"] for s in queue.json()] == []

    # arxivda bor — bu ilgari imkonsiz edi
    archive = await api.get("/api/v1/submissions?status=approved,paid", headers=admin)
    assert [s["id"] for s in archive.json()] == [submission_id]

    everything = await api.get("/api/v1/submissions?limit=50", headers=admin)
    assert submission_id in [s["id"] for s in everything.json()]


async def test_archive_paginates(api):
    """«Yana yuklash» — `offset` ishlashi kerak."""
    mechanic = await login(api, MECHANIC_TG)
    admin = auth_header((await login(api, ADMIN_TG))["access_token"])
    ids = [await _submit_repair(api, mechanic["access_token"]) for _ in range(3)]

    first = await api.get("/api/v1/submissions?limit=2&offset=0", headers=admin)
    second = await api.get("/api/v1/submissions?limit=2&offset=2", headers=admin)
    assert len(first.json()) == 2 and len(second.json()) == 1

    seen = [s["id"] for s in first.json()] + [s["id"] for s in second.json()]
    assert sorted(seen) == sorted(ids)  # takrorlanmaydi, tushib qolmaydi


async def test_reporter_archive_still_shows_only_own_reports(api):
    """R: ustaga boshqaning hisoboti ochilmaydi — arxiv ham xuddi shunday."""
    mechanic = await login(api, MECHANIC_TG)
    admin_auth = await login(api, ADMIN_TG)
    await _submit_repair(api, mechanic["access_token"])

    # admin o'z nomidan hisobot yozadi (R1a — avtomatik tasdiqlanadi)
    admin_submission = await _submit_repair(api, admin_auth["access_token"])

    as_mechanic = await api.get(
        "/api/v1/submissions?limit=50", headers=auth_header(mechanic["access_token"])
    )
    ids = [s["id"] for s in as_mechanic.json()]
    assert admin_submission not in ids


async def test_accountant_payment_flow(api):
    """⭐ Buxgalter to'lov oqimi API orqali — qarz → to'lov → tarix → bekor.

    Bu test aynan shu sabab yozilgan: `POST /payments` prodda 500 bergan edi.
    Servis darajasidagi testlar buni ushlamadi, chunki xato **javobni
    serializatsiya qilishda** edi: yangi yaratilgan `Payment` da `employee`
    bog'lanishi yuklanmagan bo'lib, unga murojaat lazy load'ni chaqirardi
    (`MissingGreenlet`).
    """
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)
    accountant = await login(api, ACCOUNTANT_TG)
    m_token, a_token, acc_token = (
        mechanic["access_token"],
        admin["access_token"],
        accountant["access_token"],
    )

    submission_id = await _submit_repair(api, m_token, price=250000)
    approved = await api.post(
        f"/api/v1/submissions/{submission_id}/approve",
        headers=auth_header(a_token),
        json={},
    )
    assert approved.status_code == 200, approved.text

    # qarzdorlar ro'yxati
    debts = await api.get("/api/v1/debts", headers=auth_header(acc_token))
    assert debts.status_code == 200, debts.text
    assert float(debts.json()["total"]) == 250000.0
    employee_id = debts.json()["employees"][0]["employee_id"]

    items = await api.get(f"/api/v1/debts/{employee_id}", headers=auth_header(acc_token))
    assert items.status_code == 200
    assert float(items.json()[0]["debt"]) == 250000.0

    # qisman to'lov — javob to'liq serializatsiya bo'lishi kerak
    paid = await api.post(
        "/api/v1/payments",
        headers=auth_header(acc_token),
        json={"employee_id": employee_id, "amount": 100000},
    )
    assert paid.status_code == 200, paid.text
    body = paid.json()
    assert body["employee_name"]  # ← lazy load bo'lsa shu yerda 500 bo'lardi
    assert float(body["amount"]) == 100000.0
    assert body["allocations"][0]["fully_paid"] is False
    payment_id = body["id"]

    after = await api.get("/api/v1/debts", headers=auth_header(acc_token))
    assert float(after.json()["total"]) == 150000.0

    # qarzdan ortiq to'lov — avansga aylanadi (P7)
    advance = await api.post(
        "/api/v1/payments",
        headers=auth_header(acc_token),
        json={"employee_id": employee_id, "amount": 200000},
    )
    assert advance.status_code == 200, advance.text
    summary = await api.get("/api/v1/debts", headers=auth_header(acc_token))
    assert float(summary.json()["total"]) == 0.0
    assert float(summary.json()["advance_total"]) == 50000.0

    history = await api.get("/api/v1/payments", headers=auth_header(acc_token))
    assert history.status_code == 200
    assert len(history.json()) == 2

    # ⭐ To'lov kartochkasi: allokatsiyada hisobot RAQAMI va joriy holati.
    # Raqamsiz Mini App'da «#12» degan ichki id ko'rinardi; `fully_paid` esa
    # ro'yxatda doim `false` bo'lib qolardi (faqat yaratishda to'ldirilardi).
    latest = history.json()[0]["allocations"][0]
    assert latest["number"].startswith("WO-"), latest
    assert latest["fully_paid"] is True
    assert latest["submission_id"] == submission_id

    # bekor qilish — qarz qaytadi
    voided = await api.post(
        f"/api/v1/payments/{payment_id}/void",
        headers=auth_header(acc_token),
        json={"reason": "Xato kiritildi"},
    )
    assert voided.status_code == 200, voided.text
    assert voided.json()["voided_at"] is not None


async def test_payment_requires_finance_role(api):
    """Usta to'lov qayd eta olmaydi."""
    mechanic = await login(api, MECHANIC_TG)
    response = await api.post(
        "/api/v1/payments",
        headers=auth_header(mechanic["access_token"]),
        json={"employee_id": 1, "amount": 1000},
    )
    assert response.status_code == 403


# --- ⭐ O'z pul holati (`/me/balance`) -----------------------------------------


async def test_mechanic_sees_own_debt_and_advance(api):
    """Usta bosh ekranda «bizning qarzimiz» va «avans»ni ko'radi.

    ⚠️ Bu yagona pul endpointi bo'lib, u **buxgalter huquqisiz** ochiladi:
    boshqa birovniki emas, o'z raqami. Qolgan `/debts`, `/payments` — hamon
    `FinanceDep` ostida (pastdagi test).
    """
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)
    accountant = await login(api, ACCOUNTANT_TG)
    m_token, a_token, acc_token = (
        mechanic["access_token"],
        admin["access_token"],
        accountant["access_token"],
    )
    employee_id = mechanic["employee"]["id"]

    empty = await api.get("/api/v1/me/balance", headers=auth_header(m_token))
    assert empty.status_code == 200, empty.text
    assert float(empty.json()["debt"]) == 0.0
    assert float(empty.json()["advance"]) == 0.0

    submission_id = await _submit_repair(api, m_token, price=250000)
    await api.post(
        f"/api/v1/submissions/{submission_id}/approve",
        headers=auth_header(a_token),
        json={},
    )

    owed = (await api.get("/api/v1/me/balance", headers=auth_header(m_token))).json()
    assert float(owed["debt"]) == 250000.0
    assert owed["count"] == 1
    assert float(owed["advance"]) == 0.0

    # qarzdan ko'p to'lanadi → ortig'i avans (P7)
    await api.post(
        "/api/v1/payments",
        headers=auth_header(acc_token),
        json={"employee_id": employee_id, "amount": 300000},
    )
    after = (await api.get("/api/v1/me/balance", headers=auth_header(m_token))).json()
    assert float(after["debt"]) == 0.0
    assert after["count"] == 0
    assert float(after["advance"]) == 50000.0


async def test_balance_is_own_only(api):
    """Har kim faqat o'z raqamini oladi — `employee_id` parametri yo'q."""
    mechanic = await login(api, MECHANIC_TG)
    admin = await login(api, ADMIN_TG)
    a_token = admin["access_token"]

    submission_id = await _submit_repair(api, mechanic["access_token"], price=250000)
    await api.post(
        f"/api/v1/submissions/{submission_id}/approve",
        headers=auth_header(a_token),
        json={},
    )

    #  Ustaning qarzi adminning `/me/balance` iga tushmaydi
    admin_balance = (await api.get("/api/v1/me/balance", headers=auth_header(a_token))).json()
    assert float(admin_balance["debt"]) == 0.0

    #  Umumiy qarz ro'yxati esa hamon buxgalter huquqini talab qiladi
    forbidden = await api.get(
        "/api/v1/debts", headers=auth_header(mechanic["access_token"])
    )
    assert forbidden.status_code == 403
