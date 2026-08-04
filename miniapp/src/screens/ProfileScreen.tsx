/** Profil: rol, til, aloqa ma'lumotlari. */

import * as api from '../api';
import { setLocale, t } from '../i18n';
import type { AuthResponse, Lang } from '../types';
import { Avatar, Card, Row } from '../ui';

interface Props {
  auth: AuthResponse;
  onLangChange(lang: Lang): void;
}

export function ProfileScreen({ auth, onLangChange }: Props) {
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
    </>
  );
}
