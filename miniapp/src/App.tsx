/** Ilova qobig'i: auth, oddiy navigatsiya, Telegram BackButton. */

import { useCallback, useEffect, useState } from 'react';

import * as api from './api';
import { ApiError } from './api';
import { setLocale, t } from './i18n';
import { DetailScreen } from './screens/DetailScreen';
import { FormScreen } from './screens/FormScreen';
import { HomeScreen } from './screens/HomeScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { isTelegram, tg } from './telegram';
import type { AuthResponse, Lang } from './types';
import { Skeleton, useToast } from './ui';

type Route =
  | { name: 'home' }
  | { name: 'form'; id: number }
  | { name: 'detail'; id: number }
  | { name: 'profile' };

export function App() {
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [error, setError] = useState('');
  const [stack, setStack] = useState<Route[]>([{ name: 'home' }]);
  const [toast, showToast] = useToast();
  const route = stack[stack.length - 1];

  const push = useCallback((next: Route) => setStack((prev) => [...prev, next]), []);
  const pop = useCallback(
    () => setStack((prev) => (prev.length > 1 ? prev.slice(0, -1) : prev)),
    [],
  );
  const reset = useCallback(() => setStack([{ name: 'home' }]), []);

  useEffect(() => {
    if (!isTelegram) {
      setError(t('open_in_telegram'));
      return;
    }
    api
      .login()
      .then((response) => {
        setLocale(response.employee.lang);
        setAuth(response);
      })
      .catch((err: ApiError) => {
        setError(err.code === 'not_in_registry' ? t('not_in_registry') : err.message);
      });
  }, []);

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

  return (
    <div className="app">
      {route.name !== 'home' ? null : (
        <div className="header">
          <h1>
            {auth.employee.role.icon} NovaCore — {auth.employee.role.name}
          </h1>
          <button
            type="button"
            className="chip"
            onClick={() => push({ name: 'profile' })}
            aria-label={t('profile')}
          >
            👤
          </button>
        </div>
      )}

      {route.name === 'home' ? (
        <HomeScreen
          auth={auth}
          onOpen={(id) => push({ name: 'detail', id })}
          onCreate={(code) => void createReport(code)}
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

      {toast}
    </div>
  );
}
