/** 📢 E'lon — admin bitta xabarni barcha xodimlarga yuboradi (faqat admin).
 *
 * Yetkazish bot orqali, Postgres `notifications` outbox ustida: shuning uchun
 * yuborish javobida faqat navbatga qo'yilganlar soni bo'ladi, haqiqiy
 * «yetkazildi/xato» hisobi tarix ro'yxatida keyinroq to'ladi.
 *
 * ⚠️ Matn XOM yuboriladi — HTML escape serverda (botga uzatishda) qilinadi,
 * chunki bot `parse_mode=HTML` bilan yuboradi. Tarixda esa admin yozgan matn
 * o'zgarishsiz ko'rinishi kerak.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { dateTime } from '../format';
import { t } from '../i18n';
import { confirmAction, haptic } from '../telegram';
import type { Broadcast } from '../types';
import { Card, Row, Skeleton } from '../ui';

/** Backend bilan bir xil chegara (`domain/broadcast.MAX_BODY`). */
const MAX_BODY = 3500;

interface Props {
  onDone(message: string): void;
}

/** Karnay — ro'yxatdagi belgi. Emoji emas: platformalar orasida sakramaydi. */
function Megaphone() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 10v4h4l6 4V6l-6 4zM8 14v4M18 9.5a3.5 3.5 0 0 1 0 5" />
    </svg>
  );
}

export function BroadcastScreen({ onDone }: Props) {
  const [body, setBody] = useState('');
  const [rows, setRows] = useState<Broadcast[] | null>(null);
  /** Tarix yuklanmadi. ⚠️ Bo'sh ro'yxatdan farqlanadi: aks holda xatolik
   *  «hali e'lon yuborilmagan» bo'lib ko'rinadi va admin matnni qayta yuboradi. */
  const [historyFailed, setHistoryFailed] = useState(false);
  /** Tarixda to'liq ochilgan e'lon (matn odatda 3 qatordan keyin kesiladi). */
  const [openId, setOpenId] = useState<number | null>(null);
  /** null — hali noma'lum (yuklanmoqda yoki ro'yxat kelmadi). */
  const [recipients, setRecipients] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const reload = useCallback(() => {
    setHistoryFailed(false);
    setRows(null);
    api
      .listBroadcasts(20)
      .then(setRows)
      .catch(() => setHistoryFailed(true));
  }, []);

  useEffect(reload, [reload]);

  useEffect(() => {
    // Faqat ma'lumot uchun: haqiqiy sonni server javobda qaytaradi. Xodim
    // e'lonni botda oladi, shuning uchun bog'lanmaganlar sanalmaydi.
    api
      .adminEmployees()
      .then((list) =>
        setRecipients(list.filter((e) => e.status === 'active' && e.tg_linked).length),
      )
      .catch(() => setRecipients(null));
  }, []);

  const length = body.trim().length;
  const tooLong = length > MAX_BODY;
  const canSend = !busy && length > 0 && !tooLong && recipients !== 0;

  async function send() {
    if (busy) return;
    // ⚠️ Tasdiq oynasi ham `try` ichida: `showConfirm` eski klientda yoki oldingi
    // popup yopilmagan bo'lsa istisno tashlaydi. Ilgari u `try` dan tashqarida
    // edi va istisno hech kim ushlamas — tugma bosilardi, lekin ekranda mutlaqo
    // hech narsa o'zgarmasdi.
    setBusy(true);
    setError('');
    try {
      const question =
        recipients === null
          ? t('broadcast_confirm_any')
          : t('broadcast_confirm', { n: recipients });
      if (!(await confirmAction(question))) return;

      const sent = await api.sendBroadcast(body.trim());
      haptic('success');
      setBody('');
      reload();
      onDone(t('broadcast_sent', { n: sent.recipients_total }));
    } catch (err) {
      haptic('error');
      // Tarmoq uzilganda amal bajarilgan-bajarilmagani noma'lum: so'rov serverga
      // yetib borib, javob yo'lda yo'qolgan bo'lishi mumkin. Shuning uchun
      // «yuborilmadi» deyilmaydi — tarixni tekshirish taklif qilinadi.
      const fail = err as ApiError;
      setError(
        fail?.code === 'network'
          ? t('broadcast_unknown')
          : fail?.message || t('broadcast_error'),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="header">
        <h1>{t('broadcast')}</h1>
      </div>

      <Card>
        <p className="hint" style={{ marginTop: 0 }}>
          {t('broadcast_hint')}
        </p>

        <textarea
          value={body}
          rows={7}
          placeholder={t('broadcast_placeholder')}
          onChange={(e) => setBody(e.target.value)}
        />
        <p className={tooLong ? 'error' : 'hint'}>
          {t('broadcast_counter', { n: length, max: MAX_BODY })}
        </p>
        {tooLong ? <p className="error">{t('broadcast_too_long', { max: MAX_BODY })}</p> : null}

        <Row
          label={t('broadcast_recipients')}
          value={recipients === null ? '—' : recipients}
          tone={recipients ? 'accent' : undefined}
        />
        {recipients === 0 ? <p className="hint">{t('broadcast_no_recipients')}</p> : null}
        {error ? <p className="error">{error}</p> : null}

        <button type="button" disabled={!canSend} onClick={() => void send()}>
          {t('broadcast_send')}
        </button>
      </Card>

      <Card title={t('broadcast_history')}>
        {historyFailed ? (
          <>
            <p className="error">{t('broadcast_history_error')}</p>
            <button type="button" className="btn-secondary" onClick={reload}>
              {t('retry')}
            </button>
          </>
        ) : null}
        {!historyFailed && rows === null ? <Skeleton count={2} /> : null}
        {rows?.length === 0 ? <p className="muted">{t('broadcast_empty')}</p> : null}

        {rows?.map((item) => (
          // Bosilganda matn to'liq ochiladi — yuborilgan e'lonni o'qishning
          // boshqa yo'li yo'q (R9: bu yagona doimiy yozuv).
          <button
            type="button"
            className="list-item list-item-top"
            key={item.id}
            onClick={() => setOpenId(openId === item.id ? null : item.id)}
          >
            <span className="li-mark tone-talk">
              <Megaphone />
            </span>
            <span className="li-body">
              <span className="li-top">
                <strong>{item.author_name}</strong>
                <span className="li-amount">👥 {item.recipients_total}</span>
              </span>
              {/* Uch holat belgisi bir qatorga sig'masligi mumkin (ayniqsa
                  375 px'da) — o'ralishga ruxsat, aks holda «xato» soni kesiladi. */}
              <span className="badge badge-wrap">
                <span>{dateTime(item.created_at)}</span>
                {item.delivered ? (
                  <span className="status status-good">
                    {item.delivered} {t('broadcast_delivered')}
                  </span>
                ) : null}
                {item.pending ? (
                  <span className="status status-wait">
                    {item.pending} {t('broadcast_pending')}
                  </span>
                ) : null}
                {item.failed ? (
                  <span className="status status-bad">
                    {item.failed} {t('broadcast_failed')}
                  </span>
                ) : null}
              </span>
              <span
                className={openId === item.id ? 'broadcast-text is-open' : 'broadcast-text'}
              >
                {item.body}
              </span>
            </span>
          </button>
        ))}
      </Card>
    </>
  );
}
