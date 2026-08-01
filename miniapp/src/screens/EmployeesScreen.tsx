/** 👥 Xodimlar — admin reyestri: qo'shish, rol berish, bloklash/bo'shatish.
 *
 * Ikki qadamli model (docs/01-product/01-roles-and-permissions.md §7):
 * admin xodimni reyestrga kiritadi → xodim botda `/start` bosib telefonini
 * yuboradi → `tg_user_id` biriktiriladi. O'z-o'zidan ro'yxatdan o'tish yo'q,
 * shuning uchun ro'yxatda «bog'langanmi» belgisi ko'rsatiladi.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from '../api';
import { ApiError } from '../api';
import { t } from '../i18n';
import type { Employee, EmployeeStatus, RoleSummary } from '../types';
import { Card, Skeleton } from '../ui';

interface Props {
  currentEmployeeId: number;
  onDone(message: string): void;
}

const STATUS_ICON: Record<EmployeeStatus, string> = {
  active: '🟢',
  blocked: '⛔',
  fired: '🚪',
};

export function EmployeesScreen({ currentEmployeeId, onDone }: Props) {
  const [rows, setRows] = useState<Employee[] | null>(null);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // yangi xodim formasi
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('+998');
  const [roleId, setRoleId] = useState<number | null>(null);
  const [workshop, setWorkshop] = useState('');

  const reload = useCallback(() => {
    api.adminEmployees().then(setRows).catch(() => setRows([]));
    api
      .adminRoles()
      .then((list) => {
        setRoles(list);
        setRoleId((prev) => prev ?? list.find((r) => r.kind === 'reporter')?.id ?? null);
      })
      .catch(() => setRoles([]));
  }, []);

  useEffect(reload, [reload]);

  async function act<T>(action: () => Promise<T>, message: string) {
    setBusy(true);
    setError('');
    try {
      await action();
      reload();
      onDone(message);
      return true;
    } catch (err) {
      setError((err as ApiError).message);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function add() {
    if (!roleId) return;
    const ok = await act(
      () =>
        api.createEmployee({
          full_name: name.trim(),
          phone: phone.trim(),
          role_id: roleId,
          workshop_name: workshop.trim() || null,
        }),
      t('employee_added'),
    );
    if (ok) {
      setAdding(false);
      setName('');
      setPhone('+998');
      setWorkshop('');
    }
  }

  return (
    <>
      <div className="header">
        <h1>{t('employees')}</h1>
      </div>
      {error ? <p className="error">{error}</p> : null}

      {adding ? (
        <Card title={t('new_employee')}>
          <label>
            {t('full_name')}
            <input
              value={name}
              placeholder="Karimov Bekzod"
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            {t('phone')}
            <input
              value={phone}
              inputMode="tel"
              placeholder="+998901234567"
              onChange={(e) => setPhone(e.target.value)}
            />
          </label>
          <p className="muted">{t('role_kind')}</p>
          <div className="chips">
            {roles.map((role) => (
              <button
                key={role.id}
                type="button"
                className={`chip${roleId === role.id ? ' active' : ''}`}
                onClick={() => setRoleId(role.id)}
              >
                {role.icon} {role.name_uz}
              </button>
            ))}
          </div>
          <label>
            {t('workshop_optional')}
            <input value={workshop} onChange={(e) => setWorkshop(e.target.value)} />
          </label>
          <p className="hint">{t('employee_link_hint')}</p>
          <div className="btn-row">
            <button
              type="button"
              onClick={() => void add()}
              disabled={busy || !name.trim() || phone.trim().length < 9 || !roleId}
            >
              {t('save')}
            </button>
            <button type="button" className="btn-secondary" onClick={() => setAdding(false)}>
              {t('cancel')}
            </button>
          </div>
        </Card>
      ) : (
        <button type="button" onClick={() => setAdding(true)} style={{ marginBottom: 12 }}>
          {t('new_employee')}
        </button>
      )}

      <Card title={`${t('employees')} · ${rows?.length ?? ''}`}>
        {rows === null ? <Skeleton count={3} /> : null}
        {rows?.length === 0 ? <p className="muted">{t('no_employees')}</p> : null}

        {rows?.map((row) => (
          <div className="builder-field" key={row.id}>
            <div className="builder-field-head">
              <button
                type="button"
                className="link"
                onClick={() => setOpen(open === row.id ? null : row.id)}
              >
                <strong>
                  {STATUS_ICON[row.status]} {row.full_name}
                </strong>
                <span className="badge">
                  {row.role.icon} {row.role.name} · {row.phone} ·{' '}
                  {row.tg_linked ? '🔗' : `⏳ ${t('not_linked')}`}
                </span>
              </button>
            </div>

            {open === row.id ? (
              <div className="builder-field-body">
                {row.id === currentEmployeeId ? (
                  <p className="hint">{t('this_is_you')}</p>
                ) : null}

                <p className="muted">{t('change_role')}</p>
                <div className="chips">
                  {roles.map((role) => (
                    <button
                      key={role.id}
                      type="button"
                      className={`chip${row.role_id === role.id ? ' active' : ''}`}
                      disabled={busy || row.role_id === role.id}
                      onClick={() =>
                        void act(
                          () => api.setEmployeeRole(row.id, role.id),
                          t('saved_ok'),
                        )
                      }
                    >
                      {role.icon} {role.name_uz}
                    </button>
                  ))}
                </div>

                <p className="muted">{t('status')}</p>
                <div className="chips">
                  {(['active', 'blocked', 'fired'] as EmployeeStatus[]).map((status) => (
                    <button
                      key={status}
                      type="button"
                      className={`chip${row.status === status ? ' active' : ''}`}
                      disabled={busy || row.status === status}
                      onClick={() =>
                        void act(
                          () => api.setEmployeeStatus(row.id, status),
                          t('saved_ok'),
                        )
                      }
                    >
                      {STATUS_ICON[status]} {t(`status_${status}`)}
                    </button>
                  ))}
                </div>
                <p className="hint">{t('fired_keeps_data')}</p>
              </div>
            ) : null}
          </div>
        ))}
      </Card>
    </>
  );
}
