"""Tigris (S3) bucketni tozalash — barcha yetim media obyektlarini o'chiradi.

DB media qatorlari allaqachon o'chirilgan → bucketdagi barcha obyekt yetim.
CONFIRM=YES bo'lsa: avval hammasini /tmp ichida ZIP zaxira qiladi, keyin o'chiradi.

Ishlatish:
    DRY-RUN:  python3 clean_tigris.py
    O'chirish: CONFIRM=YES python3 clean_tigris.py
"""
import os
import zipfile

import boto3

from app.core.config import settings

CONFIRM = os.environ.get("CONFIRM") == "YES"


def client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )


def main() -> None:
    c = client()
    bucket = settings.s3_bucket
    keys: list[str] = []
    total_bytes = 0
    for page in c.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for o in page.get("Contents", []):
            keys.append(o["Key"])
            total_bytes += o["Size"]
    print(f"BUCKET: {bucket}")
    print(f"Obyekt: {len(keys)}, hajm: {total_bytes / 1024 / 1024:.2f} MB")

    if not keys:
        print("Bucket allaqachon bo'sh. Hech narsa qilinmadi.")
        return

    if not CONFIRM:
        print("\nDRY-RUN — hech narsa o'chirilmadi. Haqiqiy o'chirish: CONFIRM=YES.")
        return

    # --- ZAXIRA: barcha obyektni bitta ZIP ga ---
    stamp = keys and __import__("datetime").datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    zip_path = f"/tmp/tigris_media_backup_{stamp}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for k in keys:
            body = c.get_object(Bucket=bucket, Key=k)["Body"].read()
            z.writestr(k, body)
    print(f"Zaxira ZIP yozildi: {zip_path} ({os.path.getsize(zip_path) / 1024 / 1024:.2f} MB)")

    # --- O'CHIRISH: 1000 tadan partiya bilan ---
    deleted = 0
    for i in range(0, len(keys), 1000):
        batch = [{"Key": k} for k in keys[i : i + 1000]]
        resp = c.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
        errs = resp.get("Errors", [])
        if errs:
            print("XATOLAR:", errs[:5])
        deleted += len(batch) - len(errs)
    print(f"O'chirildi: {deleted} obyekt")

    # --- Tekshiruv ---
    left = c.list_objects_v2(Bucket=bucket).get("KeyCount", 0)
    print(f"Bucketda qolgan obyekt: {left} (kutilgan 0)")
    print("Zaxira:", zip_path)


if __name__ == "__main__":
    main()
