/** Ilova qobig'i: auth, pastki navigatsiya, Telegram BackButton.
 *
 * Navigatsiya ikki qatlamli:
 *  • **Tab** — ildiz bo'limlar (pastki panel). Tanlansa stek almashadi.
 *  • **Push** — vazifa ekranlari (kartochka, forma, tahrir). Ular tab ustiga
 *    qo'yiladi, orqaga qaytish Telegram BackButton bilan. Push turganda pastki
 *    panel yashiriladi — diqqat bitta vazifada qolsin.
 */

import { useCallback, useEffect, useState } from 'react';

import * as api from './api';
import { ApiError } from './api';
import { setLocale, t } from './i18n';
import { BuilderScreen } from './screens/BuilderScreen';
import { DetailScreen } from './screens/DetailScreen';
import { EmployeesScreen } from './screens/EmployeesScreen';
import { FormScreen } from './screens/FormScreen';
import { HomeScreen } from './screens/HomeScreen';
import { PeriodScreen } from './screens/PeriodScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { ReportsScreen } from './screens/ReportsScreen';
import { RoleEditScreen } from './screens/RoleEditScreen';
import { TemplateEditScreen } from './screens/TemplateEditScreen';
import { tg, waitForInitData } from './telegram';
import type { AuthResponse, Lang, RoleKind } from './types';
import { Skeleton, TabBar, useToast } from './ui';
import type { Tab } from './ui';

type Route =
  | { name: 'home' }
  | { name: 'form'; id: number }
  | { name: 'detail'; id: number }
  | { name: 'profile' }
  | { name: 'builder' }
  | { name: 'employees' }
  | { name: 'reports' }
  | { name: 'period' }
  | { name: 'template'; id: number | null }
  | { name: 'role'; id: number | null };

/** Ildiz bo'limlar — rolga qarab. Qolgani (xodimlar, konstruktor) bosh
 *  ekrandagi admin bo'limidan ochiladi: pastki panel 4 tadan oshmasin. */
function tabsFor(kind: RoleKind): Tab[] {
  const home: Tab = { key: 'home', icon: 'home', label: t('nav_home') };
  const profile: Tab = { key: 'profile', icon: 'profile', label: t('nav_profile') };
  if (kind === 'reporter') return [home, profile];
  return [
    home,
    { key: 'reports', icon: 'reports', label: t('nav_reports') },
    { key: 'period', icon: 'period', label: t('nav_period') },
    profile,
  ];
}

export function App() {
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [error, setError] = useState('');
  const [stack, setStack] = useState<Route[]>([{ name: 'home' }]);
  const [toast, showToast] = useToast();
  const route = stack[stack.length - 1];

  const push = useCallback((next: Route) => setStack((prev) => [...prev, next]), []);

  /** Bildirishnomadagi «Ochish» → `?submission=42` → o'sha kartochka. */
  const deepLink = useCallback((): Route[] => {
    const id = Number(new URLSearchParams(window.location.search).get('submission'));
    return id > 0 ? [{ name: 'home' }, { name: 'detail', id }] : [{ name: 'home' }];
  }, []);
  const pop = useCallback(
    () => setStack((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev)),
    [],
  );
  const reset = useCallback(() => setStack([{ name: 'home' }]), []);

  useEffect(() => {
    let cancelled = false;

    // `initData` Telegram bilan asinxron handshake orqali keladi — darhol
    // bo'sh bo'lsa ham xato chiqarmasdan qisqa kutamiz (telegram.ts izohi).
    void waitForInitData().then((ready) => {
      if (cancelled) return;
      if (!ready) {
        setError(t('open_in_telegram'));
        return;
      }
      api
        .login()
        .then((response) => {
          if (cancelled) return;
          setLocale(response.employee.lang);
          setAuth(response);
          setStack(deepLink());
        })
        .catch((err: ApiError) => {
          if (cancelled) return;
          setError(err.code === 'not_in_registry' ? t('not_in_registry') : err.message);
        });
    });

    return () => {
      cancelled = true;
    };
  }, [deepLink]);

  useEffect(() => {
    const back = tg.BackButton;
    if (stack.length > 1) {
      back.show();
      back.onClick(pop);
      return () => {
        back.offClick(pop);
        back.hide();
      };
    }
    back.hide();
    return undefined;
  }, [stack.length, pop]);

  if (error) {
    return (
      <div className="app">
        <div className="card">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!auth) {
    return (
      <div className="app">
        <Skeleton count={4} />
      </div>
    );
  }

  async function createReport(templateCode: string) {
    try {
      const submission = await api.createSubmission(templateCode);
      push({ name: 'form', id: submission.id });
    } catch (err) {
      showToast((err as ApiError).message);
    }
  }

  function changeLang(lang: Lang) {
    setAuth((prev) => (prev ? { ...prev, employee: { ...prev.employee, lang } } : prev));
  }

  const tabs = tabsFor(auth.employee.role.kind);

  /** Tab — ildiz bo'lim: stek almashadi, push tarixi tozalanadi. */
  function selectTab(key: string) {
    setStack([{ name: key } as Route]);
  }

  return (
    <div className="app">
      {route.name !== 'home' ? null : (
        <div className="header">
          <h1>
            {auth.employee.full_name.split(/\s+/)[0]}
            <span className="sub">
              {auth.employee.role.icon} {auth.employee.role.name}
            </span>
          </h1>
        </div>
      )}

      {route.name === 'home' ? (
        <HomeScreen
          auth={auth}
          onOpen={(id) => push({ name: 'detail', id })}
          onCreate={(code) => void createReport(code)}
          onBuilder={() => push({ name: 'builder' })}
          onEmployees={() => push({ name: 'employees' })}
        />
      ) : null}

      {route.name === 'period' ? (
        <PeriodScreen onDone={(message) => showToast(message)} />
      ) : null}

      {route.name === 'reports' ? (
        <ReportsScreen onOpen={(id) => push({ name: 'detail', id })} />
      ) : null}

      {route.name === 'employees' ? (
        <EmployeesScreen
          currentEmployeeId={auth.employee.id}
          onDone={(message) => showToast(message)}
        />
      ) : null}

      {route.name === 'builder' ? (
        <BuilderScreen
          onEditTemplate={(id) => push({ name: 'template', id })}
          onEditRole={(id) => push({ name: 'role', id })}
        />
      ) : null}

      {route.name === 'template' ? (
        <TemplateEditScreen
          templateId={route.id}
          onDone={(message) => {
            showToast(message);
            pop();
          }}
        />
      ) : null}

      {route.name === 'role' ? (
        <RoleEditScreen
          roleId={route.id}
          onDone={(message) => {
            showToast(message);
            pop();
          }}
        />
      ) : null}

      {route.name === 'form' ? (
        <FormScreen
          submissionId={route.id}
          onDone={(message) => {
            showToast(message);
            reset();
          }}
          onCancel={reset}
        />
      ) : null}

      {route.name === 'detail' ? (
        <DetailScreen
          auth={auth}
          submissionId={route.id}
          onDone={(message) => showToast(message)}
          onEdit={(id) => push({ name: 'form', id })}
        />
      ) : null}

      {route.name === 'profile' ? (
        <ProfileScreen auth={auth} onLangChange={changeLang} />
      ) : null}

      {/* Push turganda panel yashiriladi — vazifa ekrani to'liq bo'lsin */}
      {stack.length === 1 ? (
        <TabBar tabs={tabs} active={route.name} onSelect={selectTab} />
      ) : null}

      {toast}
    </div>
  );
}
