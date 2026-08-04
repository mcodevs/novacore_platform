/** 💰 Qarz daftari — kimga qancha qarzmiz, to'lovni qayd etish (admin/buxgalter).
 *
 * Oy yopish tushunchasi YO'Q (ADR-0015). Har tasdiqlangan hisobot — muallifga
 * qarz; u to'liq yoki qisman yopiladi.
 *
 * Uch qatlam: umumiy qarz → qarzdorlar → tanlangan xodimning hisobotlari.
 *
 * ⚠️ Excel **bot orqali** keladi: Telegram WebView'da fayl yuklab olish,
 * ayniqsa iOS'da, ishonchsiz. Tugma shu yerda — fayl suhbatga tushadi.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { dateTime, money } from '../format';
import { t } from '../i18n';
import { confirmAction } from '../telegram';
import type { DebtItem, DebtSummary, EmployeeDebt, ExportKind, Payment } from '../types';
import { Card, MoneyInput, Row, Skeleton } from '../ui';

interface Props {
  onDone(message: string): void;
}

// ⚠️ `savings` («kelishuv tejamkorligi») ataylab yo'q: u savdolashish
// analitikasi, platformaning maqsadi esa hisobot va qarz. Server endpointi
// joyida qoladi — kerak bo'lsa qaytarish oson.
const EXPORTS: ExportKind[] = ['submissions', 'debts'];

type Tab = 'debts' | 'paid';

export function DebtScreen({ onDone }: Props) {
  const [tab, setTab] = useState<Tab>('debts');
  const [summary, setSummary] = useState<DebtSummary | null>(null);
  const [history, setHistory] = useState<Payment[] | null>(null);
  const [picked, setPicked] = useState<EmployeeDebt | null>(null);
  const [items, setItems] = useState<DebtItem[] | null>(null);
  const [checked, setChecked] = useState<Set<number>>(new Set());
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [debtData, paidData] = await Promise.all([
        api.debts(),
        api.payments().catch(() => []),
      ]);
      setSummary(debtData);
      setHistory(paidData);
    } catch (err) {
      setError((err as ApiError).message);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const openEmployee = useCallback(async (row: EmployeeDebt) => {
    setPicked(row);
    setItems(null);
    setChecked(new Set());
    setAmount('');
    setError('');
    try {
      setItems(await api.employeeDebts(row.employee_id));
    } catch (err) {
      setError((err as ApiError).message);
    }
  }, []);

  /** `question` berilsa — avval tasdiq so'raladi, rad etilsa hech narsa bo'lmaydi.
   *
   * ⚠️ Tasdiq oynasi ataylab `try` ICHIDA: `showConfirm` eski klientda yoki
   * oldingi popup yopilmagan bo'lsa istisno tashlaydi. Tashqarida bo'lsa uni
   * hech kim ushlamaydi — tugma bosiladi, lekin ekranda hech narsa o'zgarmaydi. */
  async function run<T>(action: () => Promise<T>, message: string, question?: string) {
    setBusy(true);
    setError('');
    try {
      if (question && !(await confirmAction(question))) return;
      await action();
      await reload();
      if (picked) {
        setItems(await api.employeeDebts(picked.employee_id));
      }
      setChecked(new Set());
      setAmount('');
      onDone(message);
    } catch (err) {
      setError((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  /** Belgilangan hisobotlarning qolgan qarzi. */
  function sumOf(ids: Set<number>): number {
    return (items ?? [])
      .filter((row) => ids.has(row.submission_id))
      .reduce((sum, row) => sum + Number(row.debt), 0);
  }

  function toggle(id: number) {
    const next = new Set(checked);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setChecked(next);
    // Alohida «belgilanganlarni to'lash» tugmasi YO'Q — chekbox to'g'ridan-to'g'ri
    // summa maydonini to'ldiradi. Bitta tugma qoladi, natija esa o'sha: summa
    // aynan belgilangan hisobotlarga taqsimlanadi (server 3-rejim). Admin
    // qiymatni tahrirlab qisman to'lashi ham mumkin.
    setAmount(next.size > 0 ? String(Math.round(sumOf(next))) : '');
  }

  const selectedTotal = sumOf(checked);

  // --- 3-qatlam: tanlangan xodimning hisobotlari ---
  if (picked) {
    // `MoneyInput` faqat raqam qaytaradi — probelni tozalash kerak emas.
    const typed = Number(amount);

    /** Tasdiq matni. Maydon ostida izoh yo'q — pul qayerga ketishi aynan shu
     *  yerda, qaror qabul qilinadigan lahzada aytiladi.
     *
     *  Qoida bitta: **FIFO, eng eski qarzdan**. Chekbox uni o'zgartirmaydi,
     *  faqat doirasini toraytiradi (belgilanganlar ichida, yana eskisidan) —
     *  shuning uchun matn ham bitta.
     *
     *  Ortiqcha summa chegarasi esa o'sha doiraga bog'liq: belgilangan
     *  hisobotlar bo'lsa boshqa qarz qolsa ham oshgani avansga tushadi. */
    const question = (): string => {
      const extra = typed - (checked.size > 0 ? selectedTotal : picked.debt);
      const head = t('pay_confirm', { sum: money(typed) });
      return extra > 0 ? `${head}\n\n${t('pay_confirm_advance', { sum: money(extra) })}` : head;
    };
    return (
      <>
        {/* Orqaga — kvadrat tugma, summa esa ism ostidagi qatorda: uchtasi
            yonma-yon turganda 375 px'da F.I.Sh. so'z o'rtasidan sinib ketardi. */}
        <div className="header">
          <button
            type="button"
            className="btn-back"
            aria-label={t('back')}
            onClick={() => setPicked(null)}
          >
            ←
          </button>
          <h1>
            {picked.full_name}
            <span className="sub sub-strong">
              {picked.debt > 0 ? money(picked.debt) : `+${money(picked.advance)}`}
            </span>
          </h1>
        </div>
        {error ? <p className="error">{error}</p> : null}

        {picked.advance > 0 ? (
          <Card>
            <Row label={t('advance')} value={money(picked.advance)} tone="good" />
            <p className="hint">{t('advance_hint')}</p>
          </Card>
        ) : null}

        <Card title={t('debt_reports')}>
          {items === null ? <Skeleton count={3} /> : null}
          {items?.length === 0 ? <p className="muted">{t('no_debt')}</p> : null}
          {/* Yorliqda faqat raqam qoladi: mashina va sana ostidagi izohga
              tushadi. Aks holda uzun matn summani ikkinchi qatorga siqib
              chiqaradi va qator o'qilmay qoladi. */}
          {items?.map((row) => (
            <label className="check-row" key={row.submission_id}>
              <input
                type="checkbox"
                checked={checked.has(row.submission_id)}
                onChange={() => toggle(row.submission_id)}
              />
              <Row
                label={`#${row.number}`}
                value={money(row.debt)}
                hint={[
                  row.vehicle,
                  dateTime(row.submitted_at),
                  Number(row.paid_amount) > 0
                    ? `${t('partly_paid')}: ${money(row.paid_amount)}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
              />
            </label>
          ))}
        </Card>

        {items ? (
          <Card title={t('make_payment')}>
            <div className="stack">
              {/* Tanlov yakuni — amal emas, xulosa: shuning uchun tugma emas,
                  yupqa urg'u qatlamidagi qator. Urg'u rangi asosiy amalda
                  (pastdagi tugmada) qoladi. */}
              {checked.size > 0 ? (
                <div className="pick-total">
                  <span className="pick-label">
                    {t('selected')}
                    <small>
                      {checked.size} {t('reports_count')}
                    </small>
                  </span>
                  <strong>{money(selectedTotal)}</strong>
                </div>
              ) : null}

              {/* Maydon bo'sh boshlanadi: na o'rnak summa, na izoh. Chekbox
                  belgilansa summa o'zi to'ladi, pul qayerga ketishi esa
                  tasdiq oynasida aytiladi — matn qaror lahzasida o'qiladi,
                  maydon ostida esa o'qilmasdan «devor» bo'lib turardi. */}
              <label className="field">
                <span>{t('pay_amount')}</span>
                <MoneyInput value={amount} onChange={setAmount} />
              </label>

              <button
                type="button"
                disabled={busy || !typed || typed <= 0}
                onClick={() =>
                  void run(
                    () =>
                      api.createPayment({
                        employee_id: picked.employee_id,
                        amount: typed,
                        // chekbox belgilangan bo'lsa — aynan ularga (qisman ham)
                        submission_ids: checked.size > 0 ? [...checked] : undefined,
                      }),
                    t('payment_saved'),
                    question(),
                  )
                }
              >
                {t('pay_by_amount')}
              </button>
            </div>
          </Card>
        ) : null}
      </>
    );
  }

  // --- 1–2-qatlam: umumiy qarz va qarzdorlar ---
  return (
    <>
      <div className="header">
        <h1>{t('nav_debts')}</h1>
      </div>
      {error ? <p className="error">{error}</p> : null}

      {/* Ko'rinishni almashtirish — amal emas, shuning uchun segment tanlovi:
          urg'u rangi haqiqiy amallarga (to'lov, eksport) qoladi. */}
      <div className="segmented" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'debts'}
          className={tab === 'debts' ? 'active' : ''}
          onClick={() => setTab('debts')}
        >
          {t('tab_debts')}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'paid'}
          className={tab === 'paid' ? 'active' : ''}
          onClick={() => setTab('paid')}
        >
          {t('tab_paid')}
        </button>
      </div>

      {summary === null ? <Skeleton count={3} /> : null}

      {tab === 'debts' && summary ? (
        <>
          <Card>
            <Row label={t('total_debt')} value={money(summary.total)} />
            {summary.advance_total > 0 ? (
              <Row
                label={t('total_advance')}
                value={money(summary.advance_total)}
                tone="good"
              />
            ) : null}
          </Card>
          <Card title={t('debtors')}>
            {summary.employees.length === 0 ? (
              <p className="muted">✅ {t('no_debt')}</p>
            ) : null}
            {summary.employees.map((row) => (
              <button
                type="button"
                className="link-row"
                key={row.employee_id}
                onClick={() => void openEmployee(row)}
              >
                <Row
                  label={row.full_name}
                  value={row.debt > 0 ? money(row.debt) : `+${money(row.advance)}`}
                  tone={row.debt > 0 ? undefined : 'good'}
                  hint={
                    row.debt > 0
                      ? `${row.count} ${t('reports_count')}${
                          row.advance > 0 ? ` · ${t('advance')}: ${money(row.advance)}` : ''
                        }`
                      : t('advance')
                  }
                />
              </button>
            ))}
          </Card>
        </>
      ) : null}

      {tab === 'paid' ? (
        <Card title={t('payment_history')}>
          {history === null ? <Skeleton count={2} /> : null}
          {history?.length === 0 ? <p className="muted">{t('no_payments')}</p> : null}
          {history?.map((row) => (
            <Row
              key={row.id}
              label={`${row.employee_name}${row.voided_at ? ` · ${t('voided')}` : ''}`}
              value={money(row.amount)}
              hint={`${dateTime(row.created_at)} · ${row.allocations.length} ${t('reports_count')}${
                row.void_reason ? ` · ${row.void_reason}` : ''
              }`}
            />
          ))}
        </Card>
      ) : null}

      {/* Eksport yorliqlari uzun («Qarzlar va to'lovlar») — yonma-yon qo'yilsa
          matn 2–3 qatorga sinadi. `.btn-grid` tor ekranda ustma-ust qo'yadi. */}
      <Card title={t('export')}>
        <p className="hint">{t('export_hint')}</p>
        <div className="btn-grid">
          {EXPORTS.map((kind) => (
            <button
              type="button"
              key={kind}
              className="btn-secondary"
              disabled={busy}
              onClick={() =>
                void run(() => api.exportToTelegram(kind), t('export_sent'))
              }
            >
              {t(`export_${kind}`)}
            </button>
          ))}
        </div>
      </Card>
    </>
  );
}
