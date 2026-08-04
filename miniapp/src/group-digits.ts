/** Summa maydonining guruhlashi: «90000» → «90 000».
 *
 * Alohida modul, chunki u sof funksiya va **testi bor** — `format.ts` esa
 * `i18n` ga bog'liq (valyuta so'zi) va Node testida import qilinmaydi.
 */

/**
 * Faqat raqamlar qoladi: tiyin kiritilmaydi (UZS'da amalda ishlatilmaydi),
 * bo'sh qiymat bo'sh qoladi.
 */
export function groupDigits(raw: string | number | null | undefined): string {
  if (raw === null || raw === undefined || raw === '') return '';
  const text = String(raw);
  // ⚠️ Serverdan kelgan qiymat kasrli bo'lishi mumkin («250000.00» — Decimal
  // JSON'da qator). Avval yaxlitlanadi: to'g'ridan-to'g'ri raqamlarni yig'ib
  // olsak nuqta tushib qolib «25 000 000» chiqadi.
  const digits = /[.,]/.test(text)
    ? String(Math.round(Number(text.replace(',', '.')) || 0))
    : text.replace(/\D/g, '');
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}
