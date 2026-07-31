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
        "odometer_photo",
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
                "odometer_value": 48250,
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
