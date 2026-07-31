/** Rol konstruktori — nom, ikonka, turi, ko'radigan shablonlar.
 *
 * Rol = NOM + `kind` + shablonlar (docs/01-product/01-roles-and-permissions.md).
 * Ruxsat matritsasi yo'q — shuning uchun bu ekranda ham checkbox'lar yo'q.
 */

import { useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { t } from '../i18n';
import type { RoleKind, RoleSummary, TemplateSummary } from '../types';
import { Card } from '../ui';

interface Props {
  roleId: number | null;
  onDone(message: string): void;
}

const KINDS: RoleKind[] = ['reporter', 'admin', 'accountant'];

export function RoleEditScreen({ roleId, onDone }: Props) {
  const [role, setRole] = useState<RoleSummary | null>(null);
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [code, setCode] = useState('');
  const [nameUz, setNameUz] = useState('');
  const [nameRu, setNameRu] = useState('');
  const [icon, setIcon] = useState('👤');
  const [kind, setKind] = useState<RoleKind>('reporter');
  const [picked, setPicked] = useState<number[]>([]);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.adminTemplates().then(setTemplates).catch(() => setTemplates([]));
    if (roleId === null) return;
    api
      .adminRoles()
      .then((rows) => {
        const found = rows.find((r) => r.id === roleId);
        if (!found) return;
        setRole(found);
        setCode(found.code);
        setNameUz(found.name_uz);
        setNameRu(found.name_ru);
        setIcon(found.icon);
        setKind(found.kind);
        setPicked(found.template_ids);
      })
      .catch((err: ApiError) => setMessage(err.message));
  }, [roleId]);

  function toggle(id: number) {
    setPicked((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function save() {
    setBusy(true);
    setMessage('');
    try {
      if (roleId === null) {
        await api.createRole({
          code,
          name_uz: nameUz,
          name_ru: nameRu || nameUz,
          icon,
          kind,
          template_ids: picked,
        });
      } else {
        await api.updateRole(roleId, {
          name_uz: nameUz,
          name_ru: nameRu || nameUz,
          icon,
          template_ids: picked,
          ...(role?.is_system ? {} : { kind }),
        });
      }
      onDone(t('saved_ok'));
    } catch (err) {
      setMessage((err as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="header">
        <h1>
          {icon} {nameUz || t('new_role')}
        </h1>
      </div>
      {message ? <p className="error">{message}</p> : null}

      <Card title={t('roles')}>
        <label>
          {t('template_code')}
          <input
            value={code}
            disabled={roleId !== null}
            placeholder="washer"
            onChange={(e) => setCode(e.target.value)}
          />
        </label>
        <label>
          {t('name_uz')}
          <input value={nameUz} onChange={(e) => setNameUz(e.target.value)} />
        </label>
        <label>
          {t('name_ru')}
          <input value={nameRu} onChange={(e) => setNameRu(e.target.value)} />
        </label>
        <label>
          {t('icon')}
          <input value={icon} maxLength={4} onChange={(e) => setIcon(e.target.value)} />
        </label>

        <p className="muted">{t('role_kind')}</p>
        <div className="chips">
          {KINDS.map((item) => (
            <button
              key={item}
              type="button"
              className={`chip${kind === item ? ' active' : ''}`}
              disabled={role?.is_system}
              onClick={() => setKind(item)}
            >
              {t(`kind_${item}`)}
            </button>
          ))}
        </div>
        {role?.is_system ? <p className="hint">{t('system_role')}</p> : null}
      </Card>

      <Card title={t('role_templates')}>
        {templates.map((tpl) => (
          <label className="switch" key={tpl.id}>
            <input
              type="checkbox"
              checked={picked.includes(tpl.id)}
              onChange={() => toggle(tpl.id)}
            />
            {tpl.icon} {tpl.name_uz}
            {tpl.is_draft ? ` · 📝 ${t('draft')}` : ''}
          </label>
        ))}
      </Card>

      <button type="button" onClick={() => void save()} disabled={busy}>
        {t('save')}
      </button>
    </>
  );
}
