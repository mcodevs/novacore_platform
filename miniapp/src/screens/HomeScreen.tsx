/** Bosh ekran — rolga qarab: usta hisoblari yoki admin paneli. */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { money, percent, shortMoney } from '../format';
import { t } from '../i18n';
import type { AuthResponse, Dashboard, Submission } from '../types';
import { Card, Hero, ReportRow, Row, Skeleton, Tile } from '../ui';

/** Tasdiqlangan ulush — hero ostidagi meter uchun. So'ralgan 0 bo'lsa to'la. */
function approvedShare(proposed: number, approved: number): number {
  return proposed > 0 ? (approved / proposed) * 100 : 100;
}

interface Props {
  auth: AuthResponse;
  onOpen(id: number): void;
  onCreate(templateCode: string): void;
  onBuilder(): void;
  onEmployees(): void;
}

/** Hisobotlar va davr — pastki paneldagi tab. Bu yerda takrorlanmaydi. */
export function HomeScreen({ auth, onOpen, onCreate, onBuilder, onEmployees }: Props) {
  const kind = auth.employee.role.kind;
  const isReporter = kind === 'reporter' || kind === 'admin';
  const seesAll = kind === 'admin' || kind === 'accountant';

  const [mine, setMine] = useState<Submission[] | null>(null);
  const [pending, setPending] = useState<Submission[] | null>(null);
  const [board, setBoard] = useState<Dashboard | null>(null);
  const [picking, setPicking] = useState(false);

  useEffect(() => {
    if (isReporter) {
      api.listSubmissions({ author_id: 'me', limit: 20 }).then(setMine).catch(() => setMine([]));
    }
    if (seesAll) {
      api.dashboard().then(setBoard).catch(() => setBoard(null));
      api
        // dashboard plitkasi bilan bir xil to'plam: ko'rilayotgani ham ro'yxatda
        // qolsin, aks holda admin ochgan hisobot ko'zdan yo'qoladi
        .listSubmissions({ status: 'submitted,in_review,price_disputed', limit: 20 })
        .then(setPending)
        .catch(() => setPending([]));
    }
  }, [isReporter, seesAll]);

  const drafts = (mine ?? []).filter((s) => s.status === 'draft' || s.status === 'reopened');
  const negotiating = (mine ?? []).filter(
    (s) => s.status === 'price_negotiation' || s.status === 'price_disputed',
  );
  const waiting = (mine ?? []).filter(
    (s) => s.status === 'submitted' || s.status === 'in_review',
  );
  const approved = (mine ?? []).filter((s) => s.status === 'approved' || s.status === 'paid');
  const myProposed = approved.reduce((sum, s) => sum + Number(s.proposed_labor_amount), 0);
  const myApproved = approved.reduce((sum, s) => sum + Number(s.labor_amount ?? 0), 0);

  function startReport() {
    if (auth.templates.length === 1) onCreate(auth.templates[0].code);
    else setPicking(true);
  }

  return (
    <>
      {seesAll ? (
        <>
          {board ? (
            <>
              <Hero
                label={`${t('this_month')} · ${board.period}`}
                value={shortMoney(board.approved_total)}
                currency={t('currency')}
                caption={t('approved_sum')}
                share={approvedShare(
                  Number(board.proposed_total),
                  Number(board.approved_total),
                )}
                foot={
                  <>
                    {t('requested')} <b>{shortMoney(board.proposed_total)}</b>
                  </>
                }
                delta={
                  Number(board.saved) > 0
                    ? `${t('saved_short')} ${shortMoney(board.saved)} · ${percent(board.saved_pct)}`
                    : undefined
                }
              />
              <div className="grid">
                <Tile
                  value={board.pending_review}
                  label={t('pending')}
                  tone={board.pending_review > 0 ? 'warn' : undefined}
                />
                <Tile
                  value={board.in_negotiation}
                  label={t('in_negotiation')}
                  tone={board.in_negotiation > 0 ? 'accent' : undefined}
                />
                <Tile value={board.vehicles_in_service} label={t('cars_in_service')} />
                <Tile value={board.approved_count} label={t('approved_month')} />
              </div>
              <Card title={t('more_details')}>
                <Row label={t('parts_total')} value={money(board.parts_total)} />
                {board.auto_approved_count > 0 ? (
                  <Row
                    label={t('auto_approved_line')}
                    value={`${board.auto_approved_count} · ${money(board.auto_approved_total)}`}
                  />
                ) : null}
              </Card>
            </>
          ) : (
            <Skeleton count={2} />
          )}

          <Card title={t('pending')}>
            {pending === null ? (
              <Skeleton count={2} />
            ) : pending.length === 0 ? (
              <p className="muted">{t('no_reports')}</p>
            ) : (
              pending.map((item) => (
                <ReportRow
                  key={item.id}
                  title={item.number}
                  amount={shortMoney(item.proposed_labor_amount)}
                  status={item.status}
                  meta={`${item.author_name} · ${item.vehicle?.plate_display ?? '—'}`}
                  onClick={() => onOpen(item.id)}
                />
              ))
            )}
          </Card>

          {kind === 'admin' ? (
            <div className="btn-row">
              <button type="button" className="btn-secondary" onClick={onEmployees}>
                {t('employees')}
              </button>
              <button type="button" className="btn-secondary" onClick={onBuilder}>
                {t('builder')}
              </button>
            </div>
          ) : null}
        </>
      ) : null}

      {isReporter ? (
        <>
          {seesAll ? null : (
            <Hero
              label={t('this_month')}
              value={shortMoney(myApproved)}
              currency={t('currency')}
              caption={t('approved_sum')}
              share={approvedShare(myProposed, myApproved)}
              foot={
                <>
                  {t('requested')} <b>{shortMoney(myProposed)}</b>
                </>
              }
              delta={
                myProposed > myApproved
                  ? `${t('reduced')} ${shortMoney(myProposed - myApproved)}`
                  : undefined
              }
            />
          )}

          <div className="grid">
            <Tile value={drafts.length} label={t('drafts')} />
            <Tile
              value={negotiating.length}
              label={t('negotiation')}
              tone={negotiating.length > 0 ? 'accent' : undefined}
            />
            <Tile
              value={waiting.length}
              label={t('awaiting_review')}
              tone={waiting.length > 0 ? 'warn' : undefined}
            />
            <Tile
              value={approved.length}
              label={t('approved_month')}
              tone={approved.length > 0 ? 'good' : undefined}
            />
          </div>

          {/* Shaxsiy pul yakuni hero'da (usta) yoki profil statistikasida
              (admin) turadi — bu yerda takrorlanmaydi. */}

          {picking ? (
            <Card title={t('choose_template')}>
              {auth.templates.map((tpl) => (
                <button
                  key={tpl.code}
                  className="list-item"
                  type="button"
                  onClick={() => onCreate(tpl.code)}
                >
                  {tpl.icon} {tpl.name}
                </button>
              ))}
            </Card>
          ) : (
            <button type="button" onClick={startReport} style={{ marginBottom: 'var(--gap)' }}>
              {t('car_arrived')}
            </button>
          )}

          <Card title={t('my_reports')}>
            {mine === null ? (
              <Skeleton count={2} />
            ) : mine.length === 0 ? (
              <p className="muted">{t('no_reports')}</p>
            ) : (
              mine.slice(0, 10).map((item) => (
                <ReportRow
                  key={item.id}
                  title={item.number}
                  amount={shortMoney(item.labor_amount ?? item.proposed_labor_amount)}
                  status={item.status}
                  meta={item.vehicle?.plate_display ?? '—'}
                  onClick={() => onOpen(item.id)}
                />
              ))
            )}
          </Card>
        </>
      ) : null}
    </>
  );
}
