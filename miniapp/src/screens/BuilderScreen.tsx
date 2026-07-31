/** 🧩 Konstruktor — shablonlar va rollar ro'yxati (faqat admin).
 *
 * docs/01-product/04-roles-and-templates.md §7: yangi rol qo'shish —
 * shablon yaratish → nashr → rol yaratish → xodimga rol berish.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from '../api';
import { t } from '../i18n';
import type { RoleSummary, TemplateSummary } from '../types';
import { Card, Skeleton } from '../ui';

interface Props {
  onEditTemplate(id: number | null): void;
  onEditRole(id: number | null): void;
}

export function BuilderScreen({ onEditTemplate, onEditRole }: Props) {
  const [templates, setTemplates] = useState<TemplateSummary[] | null>(null);
  const [roles, setRoles] = useState<RoleSummary[] | null>(null);

  const reload = useCallback(() => {
    api.adminTemplates().then(setTemplates).catch(() => setTemplates([]));
    api.adminRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  useEffect(reload, [reload]);

  return (
    <>
      <div className="header">
        <h1>{t('builder')}</h1>
      </div>
      <p className="hint">{t('builder_hint')}</p>

      <Card title={t('templates')}>
        {templates === null ? (
          <Skeleton count={2} />
        ) : (
          templates.map((tpl) => (
            <button
              key={tpl.id}
              className="list-item"
              type="button"
              onClick={() => onEditTemplate(tpl.id)}
            >
              <div>
                <strong>
                  {tpl.icon} {tpl.name_uz}
                </strong>{' '}
                <span className="muted">v{tpl.version}</span>
              </div>
              <div className="badge">
                {tpl.is_draft ? `📝 ${t('draft')}` : `✅ ${t('published')}`} ·{' '}
                {tpl.fields_count} {t('fields').toLowerCase()}
              </div>
            </button>
          ))
        )}
        <button type="button" className="btn-secondary" onClick={() => onEditTemplate(null)}>
          {t('new_template')}
        </button>
      </Card>

      <Card title={t('roles')}>
        {roles === null ? (
          <Skeleton count={2} />
        ) : (
          roles.map((role) => (
            <button
              key={role.id}
              className="list-item"
              type="button"
              onClick={() => onEditRole(role.id)}
            >
              <div>
                <strong>
                  {role.icon} {role.name_uz}
                </strong>
              </div>
              <div className="badge">
                {t(`kind_${role.kind}`)} · {role.template_ids.length} {t('templates').toLowerCase()}
                {role.is_system ? ' · 🔒' : ''}
              </div>
            </button>
          ))
        )}
        <button type="button" className="btn-secondary" onClick={() => onEditRole(null)}>
          {t('new_role')}
        </button>
      </Card>
    </>
  );
}
