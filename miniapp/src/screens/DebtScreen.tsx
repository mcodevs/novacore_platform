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
import type { DebtItem, DebtSummary, EmployeeDebt, ExportKind, Payment } from '../types';
import { Card, Row, Skeleton } from '../ui';

interface Props {
  onDone(message: string): void;
}

const EXPORTS: ExportKind[] = ['submissions', 'debts', 'savings'];

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

  async function run<T>(action: () => Promise<T>, message: string) {
    setBusy(true);
    setError('');
    try {
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

  function toggle(id: number) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const selectedTotal = (items ?? [])
    .filter((row) => checked.has(row.submission_id))
    .reduce((sum, row) => sum + Number(row.debt), 0);

  // --- 3-qatlam: tanlangan xodimning hisobotlari ---
  if (picked) {
    const typed = Number(amount.replace(/\s/g, ''));
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
              {/* 1-usul: belgilanganlarni to'liq to'lash */}
              <button
                type="button"
                disabled={busy || checked.size === 0}
                onClick={() =>
                  void run(
                    () =>
                      api.createPayment({
                        employee_id: picked.employee_id,
                        submission_ids: [...checked],
                      }),
                    t('payment_saved'),
                  )
                }
              >
                {t('pay_selected')}
                {checked.size > 0 ? (
                  <small className="btn-sub">{money(selectedTotal)}</small>
                ) : null}
              </button>

              {/* 2-usul: summa kiritish → FIFO, eng eski qarzdan.
                  Izoh ikki bosqichli: asosiysi — pul qayerga ketadi, mayda
                  qatori — ortiqchasi nima bo'ladi. Ikkalasi bir xil o'lchamda
                  bo'lsa matn devorga aylanadi. */}
              <div>
                <label className="field">
                  <span>{t('pay_amount')}</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={amount}
                    placeholder={String(picked.debt)}
                    onChange={(event) => setAmount(event.target.value)}
                  />
                </label>
                <p className="hint">
                  {items.length > 0 ? t('fifo_hint') : t('advance_only_hint')}
                </p>
                <p className="hint-sub">{t('overpay_hint')}</p>
              </div>

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
