/** Profil: rol, til, ⭐ o'z narx statistikasi (boshqalarniki emas — A-24). */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { money, percent } from '../format';
import { setLocale, t } from '../i18n';
import type { AuthResponse, Lang, PriceStats } from '../types';
import { Avatar, Card, Row, Skeleton } from '../ui';

interface Props {
  auth: AuthResponse;
  onLangChange(lang: Lang): void;
}

export function ProfileScreen({ auth, onLangChange }: Props) {
  const [stats, setStats] = useState<PriceStats | null>(null);
  const isReporter = auth.employee.role.kind !== 'accountant';

  useEffect(() => {
    if (isReporter) api.myPriceStats().then(setStats).catch(() => setStats(null));
  }, [isReporter]);

  async function switchLang(lang: Lang) {
    await api.setLang(lang);
    setLocale(lang);
    onLangChange(lang);
  }

  return (
    <>
      <div className="profile-head">
        <Avatar name={auth.employee.full_name} />
        <div className="who">
          <div className="name">{auth.employee.full_name}</div>
          <div className="meta">
            {auth.employee.role.icon} {auth.employee.role.name}
          </div>
        </div>
      </div>

      <Card>
        <Row label={t('phone')} value={auth.employee.phone} />
        {auth.employee.workshop_name ? (
          <Row label={t('workshop')} value={auth.employee.workshop_name} />
        ) : null}
      </Card>

      <Card title={t('language')}>
        <div className="chips">
          <button
            type="button"
            className={`chip${auth.employee.lang === 'uz' ? ' active' : ''}`}
            onClick={() => void switchLang('uz')}
          >
            🇺🇿 O'zbekcha
          </button>
          <button
            type="button"
            className={`chip${auth.employee.lang === 'ru' ? ' active' : ''}`}
            onClick={() => void switchLang('ru')}
          >
            🇷🇺 Русский
          </button>
        </div>
      </Card>

      {isReporter ? (
        <Card title={t('my_price_behaviour')}>
          {stats === null ? (
            <Skeleton count={1} />
          ) : stats.lines_total === 0 ? (
            <p className="muted">{t('no_reports')}</p>
          ) : (
            <>
              <Row label={t('stats_lines')} value={stats.lines_total} />
              <Row
                label={t('stats_reduced')}
                value={`${stats.lines_reduced} · ${money(stats.reduction_total)}`}
              />
              <Row
                label={t('stats_avg_reduction')}
                value={percent(stats.avg_reduction_pct)}
              />
              <Row label={t('stats_disputes')} value={stats.disputes} />
              <p className="hint">
                {Number(stats.avg_reduction_pct) < 10
                  ? t('stats_hint_good')
                  : t('stats_hint_high')}
              </p>
            </>
          )}
        </Card>
      ) : null}
    </>
  );
}
