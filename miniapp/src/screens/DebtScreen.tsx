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

type Tab = 'debts' | 'advance' | 'paid';

const TABS: Tab[] = ['debts', 'advance', 'paid'];

export function DebtScreen({ onDone }: Props) {
  const [tab, setTab] = useState<Tab>('debts');
  const [summary, setSummary] = useState<DebtSummary | null>(null);
  const [history, setHistory] = useState<Payment[] | null>(null);
  const [picked, setPicked] = useState<EmployeeDebt | null>(null);
  //  tarixdan ochilgan to'lov kartochkasi (faqat o'qish uchun)
  const [paid, setPaid] = useState<Payment | null>(null);
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

  // Bir xodimda qarz ham, avans ham bo'lishi mumkin — u ikkala ro'yxatga ham
  // tushadi. Filtrlash shu yerda: server bitta ro'yxat qaytaradi.
  const debtors = (summary?.employees ?? []).filter((row) => Number(row.debt) > 0);
  const advances = (summary?.employees ?? []).filter((row) => Number(row.advance) > 0);

  // --- To'lov kartochkasi: pul qaysi ishlarga tushdi ---
  //
  // ⚠️ Faqat o'qish uchun. To'lov hech qachon tahrirlanmaydi (P5) — xato bo'lsa
  // `void` qilinadi va qarz qayta ochiladi.
  if (paid) {
    return (
      <>
        <div className="header">
          <button
            type="button"
            className="btn-back"
            aria-label={t('back')}
            onClick={() => setPaid(null)}
          >
            ←
          </button>
          <h1>
            {paid.employee_name}
            <span className="sub sub-strong">{money(paid.amount)}</span>
          </h1>
        </div>

        <Card>
          <Row label={t('payment_date')} value={dateTime(paid.created_at)} />
          {paid.note ? <Row label={t('comment')} value={paid.note} /> : null}
          {paid.voided_at ? (
            <>
              <Row label={t('voided')} value={dateTime(paid.voided_at)} />
              <p className="hint">{t('payment_voided_note')}</p>
              {paid.void_reason ? <p className="hint">💬 {paid.void_reason}</p> : null}
            </>
          ) : null}
        </Card>

        <Card title={t('payment_covers')}>
          {paid.allocations.map((row) => (
            <Row
              key={row.submission_id}
              label={`#${row.number || row.submission_id}`}
              value={money(row.amount)}
              hint={row.fully_paid ? `✅ ${t('fully_closed')}` : t('partly_closed')}
            />
          ))}
        </Card>
      </>
    );
  }

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
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={tab === key}
            className={tab === key ? 'active' : ''}
            onClick={() => setTab(key)}
          >
            {t(`tab_${key}`)}
          </button>
        ))}
      </div>

      {summary === null ? <Skeleton count={3} /> : null}

      {/* ⚠️ Qarz va avans — ikki xil ro'yxat, ataylab ikki tabda. Ilgari
          ikkalasi bitta ro'yxatda edi: qarzdorlar orasida «+60 000 Avans»
          qatorlari turib, «kimga qancha qarzmiz?» degan asosiy savolga javob
          berish qiyinlashardi. */}
      {tab === 'debts' && summary ? (
        <>
          <Card>
            <Row label={t('total_debt')} value={money(summary.total)} />
          </Card>
          <Card title={t('debtors')}>
            {debtors.length === 0 ? <p className="muted">✅ {t('no_debt')}</p> : null}
            {debtors.map((row) => (
              <button
                type="button"
                className="link-row"
                key={row.employee_id}
                onClick={() => void openEmployee(row)}
              >
                <Row
                  label={row.full_name}
                  value={money(row.debt)}
                  hint={`${row.count} ${t('reports_count')}`}
                />
              </button>
            ))}
          </Card>
        </>
      ) : null}

      {tab === 'advance' && summary ? (
        <>
          <Card>
            <Row label={t('total_advance')} value={money(summary.advance_total)} tone="good" />
            <p className="hint">{t('advance_hint')}</p>
          </Card>
          <Card title={t('advance_holders')}>
            {advances.length === 0 ? <p className="muted">{t('no_advance')}</p> : null}
            {advances.map((row) => (
              <button
                type="button"
                className="link-row"
                key={row.employee_id}
                onClick={() => void openEmployee(row)}
              >
                {/* Xodimda bir vaqtda qarz ham, avans ham bo'lishi mumkin
                    (avans yangi ish tasdiqlangunicha ishlatilmaydi) — shuning
                    uchun qarzi izohda ko'rsatiladi. */}
                <Row
                  label={row.full_name}
                  value={`+${money(row.advance)}`}
                  tone="good"
                  hint={row.debt > 0 ? t('has_debt', { sum: money(row.debt) }) : undefined}
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
          {/* Qator bosiladi: pul qaysi ishlarga taqsimlangani faqat kartochka
              ichida ko'rinadi — ro'yxatda «3 ta ish» degan son yetarli emas. */}
          {history?.map((row) => (
            <button
              type="button"
              className="link-row"
              key={row.id}
              onClick={() => setPaid(row)}
            >
              <Row
                label={`${row.employee_name}${row.voided_at ? ` · ${t('voided')}` : ''}`}
                value={money(row.amount)}
                hint={`${dateTime(row.created_at)} · ${row.allocations.length} ${t('reports_count')}`}
              />
            </button>
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
