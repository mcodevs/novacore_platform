/** Ko'rsatish holati — «qisman to'langan» qadamini qo'shadi.
 *
 * ⚠️ Serverda bunday status **YO'Q** va qo'shilmaydi. Holat mashinasi
 * o'zgarmagan: `_sync_status` hisobotni `PAID` ga faqat qarz **to'liq**
 * yopilganda o'tkazadi, ya'ni qisman to'lov davrida u hamon `APPROVED`.
 * Lekin xodim uchun «Tasdiqlangan» va «yarmi to'langan» — bir xil emas,
 * shuning uchun farq **ko'rsatishda** hisoblanadi: `paid_amount` va
 * `payable_amount` allaqachon API javobida bor.
 *
 * Alohida modul — sof funksiya, testi bor (`unwrap.ts` bilan bir uslubda).
 */

import type { SubmissionStatus } from './types';

export type DisplayStatus = SubmissionStatus | 'partly_paid';

/** Pul maydonlari serverda `Decimal` — JSON'da qator bo'lib kelishi mumkin. */
export interface PayableLike {
  status: SubmissionStatus;
  payable_amount?: number | string | null;
  paid_amount?: number | string | null;
}

export function displayStatus(row: PayableLike): DisplayStatus {
  const payable = Number(row.payable_amount ?? 0);
  const paid = Number(row.paid_amount ?? 0);
  if (row.status === 'approved' && paid > 0 && paid < payable) return 'partly_paid';
  return row.status;
}
