/** Formatlash: pul — UZS, vaqt — Asia/Tashkent. */

import { getLocale, t } from './i18n';

export function money(value: number | null | undefined): string {
  const amount = Math.round(Number(value ?? 0));
  return `${amount.toLocaleString('ru-RU').replace(/ /g, ' ')} ${t('currency')}`;
}

export function shortMoney(value: number | null | undefined): string {
  const amount = Math.round(Number(value ?? 0));
  return amount.toLocaleString('ru-RU').replace(/ /g, ' ');
}

export function dateTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  return new Intl.DateTimeFormat(getLocale() === 'ru' ? 'ru-RU' : 'en-GB', {
    timeZone: 'Asia/Tashkent',
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

export function duration(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  const total = Math.max(0, Math.round(seconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const lang = getLocale();
  const h = lang === 'ru' ? 'ч' : lang === 'uz_cyrl' ? 'с' : 's';
  const m = lang === 'ru' ? 'мин' : lang === 'uz_cyrl' ? 'дақ' : 'daq';
  if (hours && minutes) return `${hours} ${h} ${minutes} ${m}`;
  if (hours) return `${hours} ${h}`;
  return `${minutes} ${m}`;
}

export function percent(value: number | null | undefined, digits = 1): string {
  return `${Number(value ?? 0).toFixed(digits)}%`;
}

/** Foto siqish: 1600 px (uzun tomon), JPEG 0.75 → 3.5 MB ≈ 200 KB. */
export async function compressImage(file: File, maxSide = 1600, quality = 0.75): Promise<Blob> {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    const width = Math.round(bitmap.width * scale);
    const height = Math.round(bitmap.height * scale);

    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, width, height);
    bitmap.close?.();

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, 'image/jpeg', quality),
    );
    return blob ?? file;
  } catch {
    // siqib bo'lmasa — originalni yuboramiz (server MIME va hajmni tekshiradi)
    return file;
  }
}
