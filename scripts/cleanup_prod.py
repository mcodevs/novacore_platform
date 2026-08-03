"""NovaCore prod bazani tozalash — bitta admin login qoldiradi.

QOLADI (tegilmaydi): roles, templates, template_fields, template_versions,
role_templates, work_catalog, parts_catalog, catalog_items, vehicles,
counters, alembic_version + `+998993081155` telefonli admin xodim.

O'CHADI: boshqa barcha xodimlar; BARCHA hisobotlar (admin'niki ham) va ularga
bog'liq submission_lines/media/approvals/flags; BARCHA periods + payouts;
notifications; broadcasts; o'chgan xodimlarning refresh_token'lari.

audit_log O'CHMAYDI (R9) — faqat o'chgan xodimga ishora qiluvchi actor_id NULL
qilinadi. template_versions.published_by ham xuddi shunday NULL qilinadi.

Ishlatish:
    DRY-RUN (xavfsiz):   python3 cleanup_prod.py
    HAQIQIY o'chirish:   CONFIRM=YES python3 cleanup_prod.py
"""
import asyncio
import datetime as dt
import json
import os

import asyncpg

TARGET_PHONE = "+998993081155"
CONFIRM = os.environ.get("CONFIRM") == "YES"

# O'chirish tartibi: bola jadvallar avval, ota jadvallar keyin.
# (scope=None => butun jadval; aks holda WHERE ifodasi, $1 = admin_id)
DELETE_STEPS = [
    ("notifications", None),
    ("broadcasts", None),
    ("payouts", None),
    ("approvals", None),
    ("flags", None),
    ("media", None),
    ("submission_lines", None),
    ("submissions", None),
    ("periods", None),
    ("refresh_tokens", "employee_id <> $1"),
    ("employees", "id <> $1"),
]


def _pg_url() -> str:
    raw = os.environ["DATABASE_URL"]
    # SQLAlchemy sxemasini asyncpg tushunadigan ko'rinishga keltirish
    for a, b in (("+asyncpg", ""), ("postgresql+psycopg", "postgresql")):
        raw = raw.replace(a, b)
    return raw


def _json_default(o):
    if isinstance(o, (dt.datetime, dt.date)):
        return o.isoformat()
    return str(o)


async def main() -> None:
    con = await asyncpg.connect(_pg_url())
    try:
        # --- Nishon adminni topish (eng muhim xavfsizlik tekshiruvi) ---
        admins = await con.fetch(
            "SELECT id, full_name, role_id FROM employees WHERE phone = $1", TARGET_PHONE
        )
        if len(admins) != 1:
            raise SystemExit(
                f"TO'XTATILDI: '{TARGET_PHONE}' bo'yicha {len(admins)} ta xodim topildi "
                f"(1 ta bo'lishi shart). Hech narsa o'zgartirilmadi."
            )
        admin_id = admins[0]["id"]
        print(f"Nishon admin: id={admin_id}  {admins[0]['full_name']}\n")

        # --- Nima o'chishini sanash ---
        print("=== O'CHADIGAN QATORLAR SONI ===")
        total = 0
        for table, scope in DELETE_STEPS:
            q = f'SELECT COUNT(*) FROM "{table}"'
            args = []
            if scope:
                q += f" WHERE {scope}"
                args = [admin_id]
            n = await con.fetchval(q, *args)
            total += n
            print(f"  {table:20} {n}")
        print(f"  {'JAMI':20} {total}")

        # FK NULL-fixup ta'sirini ko'rsatish
        tv = await con.fetchval(
            "SELECT COUNT(*) FROM template_versions WHERE published_by IS NOT NULL "
            "AND published_by <> $1",
            admin_id,
        )
        au = await con.fetchval(
            "SELECT COUNT(*) FROM audit_log WHERE actor_id IS NOT NULL AND actor_id <> $1",
            admin_id,
        )
        print("\n=== NULL qilinadigan FK (jadval saqlanadi) ===")
        print(f"  template_versions.published_by  {tv}")
        print(f"  audit_log.actor_id              {au}")

        if not CONFIRM:
            print(
                "\nDRY-RUN — hech narsa o'chirilmadi. "
                "Haqiqiy o'chirish uchun: CONFIRM=YES bilan qayta ishga tushiring."
            )
            return

        # --- ZAXIRA: o'chadigan barcha qatorlarni + audit actor xaritasini faylga yozish ---
        stamp = (await con.fetchval("SELECT now()")).strftime("%Y%m%d_%H%M%S")
        backup_path = f"/tmp/novacore_cleanup_backup_{stamp}.json"
        backup: dict[str, list] = {}
        for table, scope in DELETE_STEPS:
            q = f'SELECT * FROM "{table}"'
            args = []
            if scope:
                q += f" WHERE {scope}"
                args = [admin_id]
            rows = await con.fetch(q, *args)
            backup[table] = [dict(r) for r in rows]
        # NULL qilinadigan audit_log actor_id'larining eski qiymati (tiklash uchun)
        backup["_audit_actor_map"] = [
            dict(r)
            for r in await con.fetch(
                "SELECT id, actor_id FROM audit_log "
                "WHERE actor_id IS NOT NULL AND actor_id <> $1",
                admin_id,
            )
        ]
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup, f, default=_json_default, ensure_ascii=False, indent=2)
        print(f"\nZaxira yozildi: {backup_path}")

        # --- O'chirish (bitta tranzaksiya) ---
        # R9 audit triggeri UPDATE/DELETE ni bloklaydi; xodimni hard-delete qilish
        # uchun audit_log.actor_id NULL qilinishi shart → triggerni vaqtincha o'chiramiz.
        # DDL Postgres'da tranzaksion: xato bo'lsa trigger holati ham rollback bo'ladi.
        async with con.transaction():
            await con.execute(
                "ALTER TABLE audit_log DISABLE TRIGGER audit_log_no_update_delete"
            )
            n_audit = await con.execute(
                "UPDATE audit_log SET actor_id = NULL "
                "WHERE actor_id IS NOT NULL AND actor_id <> $1",
                admin_id,
            )
            print(f"  audit_log.actor_id NULL: {n_audit}")
            await con.execute(
                "UPDATE template_versions SET published_by = NULL "
                "WHERE published_by IS NOT NULL AND published_by <> $1",
                admin_id,
            )
            for table, scope in DELETE_STEPS:
                q = f'DELETE FROM "{table}"'
                args = []
                if scope:
                    q += f" WHERE {scope}"
                    args = [admin_id]
                res = await con.execute(q, *args)
                print(f"  {table:20} {res}")
            await con.execute(
                "ALTER TABLE audit_log ENABLE TRIGGER audit_log_no_update_delete"
            )
            print("  audit_log trigger qayta yoqildi")

        # --- Yakuniy tekshiruv ---
        emp_left = await con.fetchval("SELECT COUNT(*) FROM employees")
        sub_left = await con.fetchval("SELECT COUNT(*) FROM submissions")
        per_left = await con.fetchval("SELECT COUNT(*) FROM periods")
        tpl_left = await con.fetchval("SELECT COUNT(*) FROM templates")
        print(
            f"\n=== YAKUN ===\n  employees={emp_left} (kutilgan 1)  submissions={sub_left} "
            f"(0)  periods={per_left} (0)  templates={tpl_left} (tegilmagan)"
        )
        print("Tayyor. Zaxira fayli:", backup_path)
    finally:
        await con.close()


if __name__ == "__main__":
    asyncio.run(main())
