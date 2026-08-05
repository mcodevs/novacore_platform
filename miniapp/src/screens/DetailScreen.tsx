/** Ko'rib chiqish ekrani.
 *
 *  Admin: narx tarixi + tasdiqlash / kamaytirish / qaytarish / rad etish.
 *  Muallif: o'z hisoboti + narx taklifiga rozilik yoki nizo.
 *  ⚠️ Narx tarixi faqat admin/buxgalterga so'raladi (R3).
 */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { displayStatus } from '../display-status';
import { dateTime, duration, money } from '../format';
import { t } from '../i18n';
import { confirmAction, haptic } from '../telegram';
import type { AuthResponse, PriceContext, Submission } from '../types';
import { Lightbox } from '../Lightbox';
import { Card, MoneyInput, Row, Skeleton, StatusBadge } from '../ui';

interface Props {
  auth: AuthResponse;
  submissionId: number;
  onDone(message: string): void;
  onEdit(id: number): void;
}

//  ⚠️ `final` («yakuniy qaror») ataylab yo'q — ADR-0023: admin nizoni bir
//  tomonlama yopa olmaydi.
type Prompt = 'reduce' | 'reject' | 'reopen' | 'dispute' | null;

export function DetailScreen({ auth, submissionId, onDone, onEdit }: Props) {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [contexts, setContexts] = useState<PriceContext[]>([]);
  const [prompt, setPrompt] = useState<Prompt>(null);
  //  qator id -> kiritilgan summa (bo'sh = narx o'zgarmaydi)
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  //  null — ko'ruvchi yopiq; son — ochilgan foto indeksi
  const [viewer, setViewer] = useState<number | null>(null);

  const isAdmin = auth.employee.role.kind === 'admin';
  const isAuthor = submission?.author_id === auth.employee.id;

  useEffect(() => {
    api
      .getSubmission(submissionId)
      .then((loaded) => {
        setSubmission(loaded);
        if (auth.employee.role.kind !== 'reporter') {
          api.priceContext(submissionId).then(setContexts).catch(() => setContexts([]));
        }
      })
      .catch((error: ApiError) => setFailure(error.message));
  }, [submissionId, auth.employee.role.kind]);

  async function run(action: () => Promise<Submission>, message: string) {
    setBusy(true);
    setFailure('');
    try {
      const updated = await action();
      setSubmission(updated);
      haptic('success');
      onDone(message);
    } catch (error) {
      haptic('error');
      setFailure((error as ApiError).message);
    } finally {
      setBusy(false);
      setPrompt(null);
      setComment('');
      setAmounts({});
    }
  }

  if (failure && !submission) return <p className="error">{failure}</p>;
  if (!submission) return <Skeleton count={4} />;

  const labor = submission.lines.filter((line) => line.kind === 'labor');
  const parts = submission.lines.filter((line) => line.kind === 'part');
  const canReview =
    isAdmin && ['submitted', 'in_review', 'price_disputed'].includes(submission.status);
  const canNegotiate = isAuthor && submission.status === 'price_negotiation';
  //  Nizoda adminning ikkitagina yo'li bor: yangi narx yoki ustaning narxi.
  //  Tasdiqlash va rad etish bu holatda serverda ham qabul qilinmaydi.
  const inDispute = submission.status === 'price_disputed';

  return (
    <>
      <div className="header">
        <h1>{submission.number}</h1>
        <StatusBadge status={displayStatus(submission)} />
      </div>

      <Card>
        <Row label={t('author')} value={submission.author_name} />
        {submission.vehicle ? (
          <Row
            label="🚘"
            value={`${submission.vehicle.plate_display} · ${submission.vehicle.brand} ${submission.vehicle.model}`}
          />
        ) : null}
        <Row label={t('arrived')} value={dateTime(submission.arrived_at)} />
        <Row
          label={t('left')}
          value={`${dateTime(submission.left_at)} (${duration(submission.downtime_seconds)})`}
        />
        {submission.auto_approved ? <p className="hint">⚙️ {t('auto_approved_line')}</p> : null}
      </Card>

      <Card title="💰">
        {/* ⚠️ Narx tarixi (o'rtacha, min–maks, «necha % hollarda kamaytirilgan»)
            bu yerda ATAYLAB YO'Q. U faqat admin narxni kamaytirayotgan
            lahzada — «Narxni kamaytirish» oynasida — ko'rsatiladi. Hisobot
            o'zi bajarilgan ish haqidagi hujjat; savdolashish raqamlari uni
            asosiy mavzuga aylantirib yuborardi. */}
        {labor.map((line) => (
          <div key={line.id} style={{ marginBottom: 10 }}>
            <div className="row">
              <span>🔧 {line.name}</span>
              <strong>
                {money(line.proposed_amount)}
                {line.approved_amount !== null &&
                Number(line.approved_amount) !== Number(line.proposed_amount)
                  ? ` → ${money(line.approved_amount)}`
                  : ''}
              </strong>
            </div>
            {line.price_change_reason ? (
              <div className="history">💬 {line.price_change_reason}</div>
            ) : null}
          </div>
        ))}
        {parts.length ? (
          <>
            <p className="muted">{t('parts')}</p>
            {parts.map((line) => (
              <div className="row" key={line.id}>
                <span>📦 {line.name} ×{line.qty}</span>
                <strong>
                  {Number(line.approved_amount ?? line.proposed_amount) > 0
                    ? money(line.approved_amount ?? line.proposed_amount)
                    : '—'}
                </strong>
              </div>
            ))}
          </>
        ) : null}
        {/* «So'radim» faqat narx haqiqatan kamaytirilgan bo'lsa ko'rsatiladi:
            teng bo'lganda ikkita bir xil raqam savdolashish bo'lmagan joyda ham
            uni ko'z oldiga keltirardi. */}
        {submission.labor_amount === null ? (
          <Row label={t('requested')} value={money(submission.proposed_labor_amount)} />
        ) : (
          <>
            {Number(submission.labor_amount) < Number(submission.proposed_labor_amount) ? (
              <Row label={t('requested')} value={money(submission.proposed_labor_amount)} />
            ) : null}
            <Row label={t('approved_sum')} value={money(submission.labor_amount)} />
          </>
        )}

        {/* ⭐ To'lov holati aynan SHU hisobot bo'yicha (ADR-0015): «to'landi» va
            «qoldi» bo'lmasa, xodim faqat umumiy qarzini ko'rardi va qaysi ish
            uchun qancha kelganini bilmasdi. `payable` — tasdiqlangan ish haqi
            + «o'z hisobimdan» qismlar (R5), shuning uchun u yuqoridagi
            «Tasdiqlandi» dan katta bo'lishi mumkin. */}
        {Number(submission.payable_amount) > 0 ? (
          <div className="pay-state">
            <Row label={t('payable_total')} value={money(submission.payable_amount)} />
            <Row
              label={t('paid')}
              value={money(submission.paid_amount)}
              tone={Number(submission.paid_amount) > 0 ? 'good' : undefined}
            />
            {Number(submission.debt) > 0 ? (
              <Row label={t('remaining')} value={money(submission.debt)} tone="accent" />
            ) : null}
          </div>
        ) : null}
      </Card>

      {submission.media.length ? (
        <Card title={t('photos')}>
          {/* Foto ilova ichida ochiladi — brauzerga chiqmaydi */}
          <div className="photos">
            {submission.media.map((item, i) => (
              <button
                key={item.id}
                type="button"
                className="photo-open"
                onClick={() => setViewer(i)}
                aria-label={t('photos')}
              >
                <img src={item.url} alt={item.field_code ?? ''} loading="lazy" />
              </button>
            ))}
          </div>
        </Card>
      ) : null}

      {typeof submission.data.comment === 'string' && submission.data.comment ? (
        <Card title={t('comment')}>
          <p>{String(submission.data.comment)}</p>
        </Card>
      ) : null}

      {/* --- Usta: narx taklifiga javob --- */}
      {canNegotiate ? (
        <Card title={t('negotiation')}>
          {/* Har bir xizmat alohida ko'rinadi — kelishuv esa BITTA (hammasiga) */}
          <div className="negotiation">
            {(() => {
              const changed = labor.filter(
                (line) =>
                  line.approved_amount !== null &&
                  Number(line.approved_amount) < Number(line.proposed_amount),
              );
              // Jami — BARCHA xizmatlar bo'yicha: tegilmagani o'z narxida qoladi
              const askedTotal = labor.reduce((s, l) => s + Number(l.proposed_amount), 0);
              const offerTotal = labor.reduce(
                (s, l) =>
                  s + Number(l.approved_amount ?? l.proposed_amount),
                0,
              );
              return (
                <>
                  {changed.map((line) => (
                    <div className="nego-line" key={line.id}>
                      <span className="nego-name">🔧 {line.name}</span>
                      <span className="nego-nums">
                        <s>{money(line.proposed_amount)}</s>
                        <strong>{money(line.approved_amount)}</strong>
                      </span>
                    </div>
                  ))}
                  {labor.length > changed.length && changed.length ? (
                    <p className="hint">{t('unchanged_lines_note')}</p>
                  ) : null}
                  <div className="nego-total">
                    <Row label={t('you_asked')} value={money(askedTotal)} />
                    <Row label={t('admin_proposed')} value={money(offerTotal)} tone="accent" />
                  </div>
                </>
              );
            })()}
          </div>
          <p className="hint">{t('auto_accept_note', { hours: 48 })}</p>
          {prompt === 'dispute' ? (
            <>
              <textarea
                placeholder={t('dispute_comment')}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
              <button
                type="button"
                disabled={busy || comment.trim().length < 5}
                onClick={() =>
                  void run(() => api.disputePrice(submissionId, comment.trim()), t('done'))
                }
              >
                {t('dispute_price')}
              </button>
            </>
          ) : (
            <div className="btn-row">
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  if (await confirmAction(t('accept_price'))) {
                    void run(() => api.acceptPrice(submissionId), t('done'));
                  }
                }}
              >
                {t('accept_price')}
              </button>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setPrompt('dispute')}
              >
                {t('dispute_price')}
              </button>
            </div>
          )}
        </Card>
      ) : null}

      {/* --- Admin: qarorlar --- */}
      {canReview ? (
        <Card>
          {prompt === null ? (
            <>
              {/* ⭐ ADR-0023 — nizoda «yakuniy qaror» YO'Q. Kelishuv ikki
                  tomonlama: admin yo yangi narx beradi, yo ustanikiga rozi
                  bo'ladi. Rad etish ham bu holatda yo'q (server ham qabul
                  qilmaydi) — ish bajarilgan, gap faqat summada. */}
              {inDispute ? <p className="hint">{t('dispute_admin_hint')}</p> : null}
              <button
                type="button"
                disabled={busy}
                onClick={async () => {
                  if (!inDispute) {
                    void run(() => api.approve(submissionId), t('done'));
                    return;
                  }
                  if (await confirmAction(t('accept_author_price_confirm'))) {
                    void run(() => api.acceptAuthorPrice(submissionId), t('done'));
                  }
                }}
              >
                {t(inDispute ? 'accept_author_price' : 'approve')}
              </button>
              <div className="btn-row" style={{ marginTop: 'var(--s-3)' }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setPrompt('reduce');
                    setAmounts({});
                  }}
                >
                  {t(inDispute ? 'propose_new_price' : 'reduce_price')}
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPrompt('reopen')}
                >
                  {t('reopen')}
                </button>
              </div>
              {!inDispute ? (
                <button
                  type="button"
                  className="btn-danger"
                  style={{ marginTop: 'var(--s-3)' }}
                  onClick={() => setPrompt('reject')}
                >
                  {t('reject')}
                </button>
              ) : null}
            </>
          ) : null}

          {/* ⭐ Har bir xizmat uchun o'z summasi — yuborilganda BITTA kelishuv */}
          {prompt === 'reduce' ? (
            <>
              <p className="hint">{t('reduce_hint')}</p>
              {labor.map((line) => {
                const ctx = contexts.find((c) => c.line_id === line.id);
                const typed = amounts[line.id] ?? '';
                const tooHigh = typed !== '' && Number(typed) > Number(line.proposed_amount);
                return (
                  <div className="nego-edit" key={line.id}>
                    <div className="row">
                      <span>🔧 {line.name}</span>
                      <strong>{money(line.proposed_amount)}</strong>
                    </div>
                    {/* Narx tarixi FAQAT shu yerda — kamaytirish qarori aynan
                        shu lahzada qabul qilinadi. Hisobot ko'rinishida u yo'q. */}
                    {ctx && ctx.count > 0 ? (
                      <div className="history">
                        📊 {t('history_avg', { n: ctx.count })}: {money(ctx.avg_approved)} ·{' '}
                        {money(ctx.min_approved)} – {money(ctx.max_approved)}
                      </div>
                    ) : null}
                    <MoneyInput
                      placeholder={t('keep_price')}
                      value={typed}
                      onChange={(digits) => setAmounts({ ...amounts, [line.id]: digits })}
                    />
                    {tooHigh ? (
                      <p className="error">{t('price_increase_forbidden')}</p>
                    ) : null}
                    {ctx?.quick_amounts?.length ? (
                      <div className="chips">
                        {ctx.quick_amounts.map((value) => (
                          <button
                            key={value}
                            type="button"
                            className={`chip${Number(typed) === Number(value) ? ' active' : ''}`}
                            onClick={() =>
                              // ⚠️ `Math.round`: serverdan «200000.00» kelishi
                              // mumkin, maydon esa faqat raqam saqlaydi.
                              setAmounts({ ...amounts, [line.id]: String(Math.round(Number(value))) })
                            }
                          >
                            {money(value)}
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}

              {(() => {
                const changes = labor
                  .filter((l) => (amounts[l.id] ?? '') !== '')
                  .map((l) => ({ line: l, value: Number(amounts[l.id]) }));
                const invalid = changes.some(
                  (c) => !(c.value >= 0) || c.value > Number(c.line.proposed_amount),
                );
                const newTotal = labor.reduce(
                  (sum, l) =>
                    sum +
                    ((amounts[l.id] ?? '') !== ''
                      ? Number(amounts[l.id])
                      : Number(l.proposed_amount)),
                  0,
                );
                return (
                  <>
                    <div className="nego-total">
                      <Row
                        label={t('requested')}
                        value={money(submission.proposed_labor_amount)}
                      />
                      <Row label={t('new_amount')} value={money(newTotal)} tone="accent" />
                    </div>
                    <label className="field">{t('reason')}</label>
                    <textarea
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                    />
                    <button
                      type="button"
                      disabled={
                        busy || !changes.length || invalid || comment.trim().length < 5
                      }
                      onClick={() => {
                        if (invalid) {
                          setFailure(t('price_increase_forbidden'));
                          haptic('error');
                          return;
                        }
                        void run(
                          () =>
                            api.proposePrice(
                              submissionId,
                              changes.map((c) => ({
                                line_id: c.line.id,
                                amount: c.value,
                              })),
                              comment.trim(),
                            ),
                          t('done'),
                        );
                      }}
                    >
                      {t('send_proposal')}
                      {changes.length ? ` (${changes.length})` : ''}
                    </button>
                  </>
                );
              })()}
            </>
          ) : null}

          {prompt === 'reject' || prompt === 'reopen' ? (
            <>
              <label className="field">{t('reason')}</label>
              <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
              <button
                type="button"
                disabled={busy || comment.trim().length < 5}
                onClick={() =>
                  void run(
                    () =>
                      prompt === 'reject'
                        ? api.reject(submissionId, comment.trim())
                        : api.reopen(submissionId, comment.trim()),
                    t('done'),
                  )
                }
              >
                {t('done')}
              </button>
            </>
          ) : null}

          {prompt !== null ? (
            <button
              type="button"
              className="btn-secondary"
              style={{ marginTop: 8 }}
              onClick={() => setPrompt(null)}
            >
              {t('cancel')}
            </button>
          ) : null}
        </Card>
      ) : null}

      {viewer !== null ? (
        <Lightbox
          items={submission.media}
          index={viewer}
          onClose={() => setViewer(null)}
        />
      ) : null}

      {failure ? <p className="error">{failure}</p> : null}

      {isAuthor && (submission.status === 'reopened' || submission.status === 'draft') ? (
        <button type="button" onClick={() => onEdit(submission.id)}>
          ✏️ {t('form_title')}
        </button>
      ) : null}
    </>
  );
}
