/** Telegram WebApp ustidan yupqa tipli qatlam.
 *  SDK Telegram tomonidan beriladi — bundle'ga qo'shimcha kutubxona kirmaydi.
 */

type ThemeParams = Record<string, string | undefined>;

interface MainButton {
  text: string;
  isVisible: boolean;
  setText(text: string): MainButton;
  show(): MainButton;
  hide(): MainButton;
  enable(): MainButton;
  disable(): MainButton;
  showProgress(leaveActive?: boolean): MainButton;
  hideProgress(): MainButton;
  onClick(cb: () => void): MainButton;
  offClick(cb: () => void): MainButton;
}

interface BackButton {
  isVisible: boolean;
  show(): BackButton;
  hide(): BackButton;
  onClick(cb: () => void): BackButton;
  offClick(cb: () => void): BackButton;
}

interface HapticFeedback {
  impactOccurred(style: 'light' | 'medium' | 'heavy'): void;
  notificationOccurred(type: 'error' | 'success' | 'warning'): void;
  selectionChanged(): void;
}

export interface WebApp {
  initData: string;
  initDataUnsafe: { user?: { id: number; language_code?: string } };
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  MainButton: MainButton;
  BackButton: BackButton;
  HapticFeedback: HapticFeedback;
  ready(): void;
  expand(): void;
  close(): void;
  showAlert(message: string, cb?: () => void): void;
  showConfirm(message: string, cb: (ok: boolean) => void): void;
  onEvent(event: string, cb: () => void): void;
  offEvent(event: string, cb: () => void): void;
}

const noop = () => {};

/** Brauzerda (Telegram'dan tashqarida) ochilganda ilova qulab tushmasin. */
const stub: WebApp = {
  initData: '',
  initDataUnsafe: {},
  colorScheme: 'light',
  themeParams: {},
  MainButton: new Proxy({} as MainButton, { get: () => () => stub.MainButton }),
  BackButton: new Proxy({} as BackButton, { get: () => () => stub.BackButton }),
  HapticFeedback: { impactOccurred: noop, notificationOccurred: noop, selectionChanged: noop },
  ready: noop,
  expand: noop,
  close: noop,
  showAlert: (m, cb) => {
    window.alert(m);
    cb?.();
  },
  showConfirm: (m, cb) => cb(window.confirm(m)),
  onEvent: noop,
  offEvent: noop,
};

export const tg: WebApp =
  (window as unknown as { Telegram?: { WebApp?: WebApp } }).Telegram?.WebApp ?? stub;

export const isTelegram = Boolean(tg.initData);

/** Telegram temasini CSS o'zgaruvchilariga ko'chiradi. */
export function applyTheme(): void {
  const root = document.documentElement;
  const params = tg.themeParams || {};
  const map: Record<string, string> = {
    bg_color: '--bg',
    secondary_bg_color: '--bg-secondary',
    text_color: '--text',
    hint_color: '--hint',
    link_color: '--link',
    button_color: '--accent',
    button_text_color: '--accent-text',
    destructive_text_color: '--danger',
  };
  for (const [key, cssVar] of Object.entries(map)) {
    const value = params[key];
    if (value) root.style.setProperty(cssVar, value);
  }
  root.dataset.scheme = tg.colorScheme;
}

export function haptic(type: 'success' | 'error' | 'warning'): void {
  try {
    tg.HapticFeedback.notificationOccurred(type);
  } catch {
    /* qo'llab-quvvatlanmasa — e'tiborsiz */
  }
}

export function confirmAction(message: string): Promise<boolean> {
  return new Promise((resolve) => tg.showConfirm(message, resolve));
}

export function init(): void {
  tg.ready();
  tg.expand();
  applyTheme();
  tg.onEvent('themeChanged', applyTheme);
}
