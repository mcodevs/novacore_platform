/** API klient: initData → JWT, avtomatik refresh, qayta urinish (zaif internet). */

import { tg } from './telegram';
import { unwrap } from './unwrap';
import type {
  AuthResponse,
  Balance,
  Broadcast,
  Dashboard,
  Employee,
  EmployeeStatus,
  Lang,
  LinkableSubmission,
  ExportKind,
  MediaItem,
  DebtItem,
  DebtSummary,
  Payment,
  PriceContext,
  RoleKind,
  RoleSummary,
  Submission,
  TemplateDefinition,
  TemplateDetail,
  TemplateSchema,
  TemplateSummary,
  Vehicle,
  WorkCatalogItem,
} from './types';

const BASE = '/api/v1';
const REFRESH_KEY = 'nc_refresh';

let accessToken = '';
let refreshToken = sessionStorage.getItem(REFRESH_KEY) ?? '';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public fields: Record<string, string> = {},
    public status = 0,
  ) {
    super(message);
  }
}

function setTokens(auth: AuthResponse): void {
  if (auth.access_token) accessToken = auth.access_token;
  if (auth.refresh_token) {
    refreshToken = auth.refresh_token;
    sessionStorage.setItem(REFRESH_KEY, refreshToken); // localStorage EMAS
  }
}

async function parse<T>(response: Response): Promise<T> {
  const text = await response.text();

  // ⚠️ Server har doim ham JSON qaytarmaydi: ishlov berilmagan xatoda
  // uvicorn oddiy matn («Internal Server Error») beradi. Uni ko'r-ko'rona
  // `JSON.parse` qilish foydalanuvchiga «JSON Parse error…» ko'rsatardi —
  // bu hech narsani anglatmaydi va asl muammoni yashiradi.
  let payload: { error?: { code?: string; message?: string; fields?: Record<string, string> } } | null =
    null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      throw new ApiError(
        response.ok ? 'bad_response' : 'server_error',
        response.ok
          ? 'Serverdan kutilmagan javob keldi'
          : `Serverda xatolik (HTTP ${response.status})`,
        {},
        response.status,
      );
    }
  }

  if (!response.ok) {
    const error = payload?.error ?? {};
    throw new ApiError(
      error.code ?? 'http_error',
      error.message ?? `HTTP ${response.status}`,
      error.fields ?? {},
      response.status,
    );
  }
  return unwrap<T>(payload);
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { ...init, headers });
  } catch {
    // Tarmoq uzildi — bir marta qayta urinamiz, lekin FAQAT o'qish so'rovlarida.
    // ⚠️ `fetch` so'rov serverga yetib borib, javob yo'lda yo'qolganda ham rad
    // etadi: yozuv so'rovini ko'r-ko'rona takrorlash amalni ikki marta bajaradi
    // (e'lon hammaga ikki marta ketardi).
    const method = (init.method ?? 'GET').toUpperCase();
    if (!retry || method !== 'GET') {
      throw new ApiError('network', 'Tarmoq bilan aloqa yo‘q');
    }
    await new Promise((r) => setTimeout(r, 1200));
    return request<T>(path, init, false);
  }

  if (response.status === 401 && retry && refreshToken) {
    try {
      const auth = await parse<AuthResponse>(
        await fetch(`${BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        }),
      );
      setTokens(auth);
      return request<T>(path, init, false);
    } catch {
      return login().then(() => request<T>(path, init, false));
    }
  }
  return parse<T>(response);
}

// --- Auth ---

export async function login(): Promise<AuthResponse> {
  const auth = await parse<AuthResponse>(
    await fetch(`${BASE}/auth/telegram`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ init_data: tg.initData }),
    }),
  );
  setTokens(auth);
  return auth;
}

export const me = () => request<AuthResponse>('/me');
export const setLang = (lang: Lang) =>
  request<Employee>('/me', { method: 'PATCH', body: JSON.stringify({ lang }) });

/** ⭐ O'z pul holati: bizning qarzimiz + avans (P7).
 *
 *  Buxgalter huquqi kerak emas — bu boshqa birovniki emas, o'z raqami.
 *  Serverda hisoblanadi: hisobotlar ro'yxati sahifalangan va avans umuman
 *  hisobotlarda emas. */
export const myBalance = () => request<Balance>('/me/balance');

// --- Spravochniklar ---

export const templateSchema = (code: string, version?: number) =>
  request<TemplateSchema>(`/templates/${code}${version ? `?version=${version}` : ''}`);

export const vehicles = (q = '') =>
  request<Vehicle[]>(`/vehicles?limit=30${q ? `&q=${encodeURIComponent(q)}` : ''}`);

export const lookupVehicle = (plate: string) =>
  request<Vehicle>(`/vehicles/lookup?plate=${encodeURIComponent(plate)}`);

export const workCatalog = (q = '') =>
  request<WorkCatalogItem[]>(`/work-catalog?limit=40${q ? `&q=${encodeURIComponent(q)}` : ''}`);

export const partsCatalog = (q = '') =>
  request<WorkCatalogItem[]>(`/parts-catalog?limit=40${q ? `&q=${encodeURIComponent(q)}` : ''}`);

export const catalogItems = (catalog: string) =>
  request<{ code: string; name: string; icon: string | null }[]>(
    `/catalog-items?catalog=${encodeURIComponent(catalog)}`,
  );

// --- Hisobotlar ---

export const listSubmissions = (params: Record<string, string | number> = {}) => {
  const query = new URLSearchParams(
    Object.entries(params).map(([k, v]) => [k, String(v)]),
  ).toString();
  return request<Submission[]>(`/submissions${query ? `?${query}` : ''}`);
};

export const getSubmission = (id: number) => request<Submission>(`/submissions/${id}`);

export const createSubmission = (template_code: string, vehicle_id?: number) =>
  request<Submission>('/submissions', {
    method: 'POST',
    body: JSON.stringify({ template_code, vehicle_id }),
  });

export const patchSubmission = (id: number, data: Record<string, unknown>) =>
  request<Submission>(`/submissions/${id}`, { method: 'PATCH', body: JSON.stringify({ data }) });

export interface LineInput {
  kind: 'labor' | 'part';
  name: string;
  qty: number;
  unit_price: number;
  catalog_id?: number | null;
  /** ⭐ «O'z hisobimdan» (ADR-0016) — narx bor = qarz bor. */
  self_funded?: boolean;
}

export const replaceLines = (id: number, lines: LineInput[]) =>
  request<Submission>(`/submissions/${id}/lines`, {
    method: 'PUT',
    body: JSON.stringify({ lines }),
  });

export const markLeft = (id: number) =>
  request<Submission>(`/submissions/${id}/mark-left`, { method: 'POST' });

export const submitSubmission = (id: number) =>
  request<Submission>(`/submissions/${id}/submit`, { method: 'POST' });

export const deleteSubmission = (id: number) =>
  request<{ ok: boolean }>(`/submissions/${id}`, { method: 'DELETE' });

// --- Tasdiqlash va narx kelishuvi ---

export const approve = (id: number, comment?: string) =>
  request<Submission>(`/submissions/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  });

export const reject = (id: number, comment: string) =>
  request<Submission>(`/submissions/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  });

export const reopen = (id: number, comment: string) =>
  request<Submission>(`/submissions/${id}/reopen`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  });

export const priceContext = (id: number) =>
  request<PriceContext[]>(`/submissions/${id}/price-context`);

export const proposePrice = (
  id: number,
  lines: { line_id: number; amount: number }[],
  comment: string,
) =>
  request<Submission>(`/submissions/${id}/propose-price`, {
    method: 'POST',
    body: JSON.stringify({ lines, comment }),
  });

export const acceptPrice = (id: number) =>
  request<Submission>(`/submissions/${id}/accept-price`, { method: 'POST' });

/** ⭐ Admin ustaning narxiga rozi bo'ladi (ADR-0023) — nizoni yopishning
 *  yagona muqobili yangi narx taklif qilish. «Yakuniy qaror» yo'q. */
export const acceptAuthorPrice = (id: number, comment?: string) =>
  request<Submission>(`/submissions/${id}/accept-author-price`, {
    method: 'POST',
    body: JSON.stringify({ comment: comment ?? null }),
  });

export const disputePrice = (id: number, comment: string) =>
  request<Submission>(`/submissions/${id}/dispute-price`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  });


/** `submission_picker` nomzodlari — qism xaridini ta'mirga bog'lash uchun. */
export const linkableSubmissions = (params: {
  template_code?: string;
  vehicle_id?: number;
  exclude_id?: number;
}) => {
  const query = new URLSearchParams(
    Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => [k, String(v)]),
  ).toString();
  return request<LinkableSubmission[]>(`/submissions/linkable?${query}`);
};

// --- Media ---

export async function uploadMedia(
  submissionId: number,
  fieldCode: string,
  file: Blob,
  kind: string,
  source: 'camera' | 'gallery' | 'unknown',
): Promise<MediaItem> {
  const form = new FormData();
  form.append('submission_id', String(submissionId));
  form.append('field_code', fieldCode);
  form.append('kind', kind);
  form.append('source', source);
  form.append('file', file, 'photo.jpg');
  return request<MediaItem>('/media/upload', { method: 'POST', body: form });
}

// --- Analitika ---

export const dashboard = () => request<Dashboard>('/reports/dashboard');

// --- Qarz daftari, to'lovlar, eksport (admin/buxgalter) — ADR-0015 ---

export const debts = () => request<DebtSummary>('/debts');

export const employeeDebts = (employeeId: number) =>
  request<DebtItem[]>(`/debts/${employeeId}`);

/** Uch rejim: `submission_ids` (chekbox) · `amount` (FIFO) · ikkalasi (qisman). */
export const createPayment = (body: {
  employee_id: number;
  submission_ids?: number[];
  amount?: number;
  note?: string;
}) => request<Payment>('/payments', { method: 'POST', body: JSON.stringify(body) });

export const payments = (employeeId?: number) =>
  request<Payment[]>(`/payments${employeeId ? `?employee_id=${employeeId}` : ''}`);

export const voidPayment = (paymentId: number, reason: string) =>
  request<Payment>(`/payments/${paymentId}/void`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });

/** Excel **bot orqali** keladi — WebView'da fayl yuklash ishonchsiz. */
export const exportToTelegram = (kind: ExportKind) =>
  request<{ ok: boolean; filename: string }>(`/reports/export?kind=${kind}`, {
    method: 'POST',
  });

// --- Konstruktorlar (Faza 2, faqat admin) ---

export const adminTemplates = () => request<TemplateSummary[]>('/admin/templates');

export const adminTemplate = (id: number) => request<TemplateDetail>(`/admin/templates/${id}`);

export const createTemplate = (definition: TemplateDefinition) =>
  request<TemplateSummary>('/admin/templates', {
    method: 'POST',
    body: JSON.stringify(definition),
  });

export const updateTemplate = (id: number, definition: TemplateDefinition) =>
  request<TemplateSummary>(`/admin/templates/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(definition),
  });

export const publishTemplate = (id: number) =>
  request<TemplateSummary>(`/admin/templates/${id}/publish`, { method: 'POST' });

export const adminRoles = () => request<RoleSummary[]>('/admin/roles');

// --- Xodimlar (faqat admin) ---

export const adminEmployees = () => request<Employee[]>('/admin/employees');

export interface EmployeeInput {
  full_name: string;
  phone: string;
  role_id: number;
  workshop_name?: string | null;
  lang?: Lang;
}

export const createEmployee = (payload: EmployeeInput) =>
  request<Employee>('/admin/employees', { method: 'POST', body: JSON.stringify(payload) });

export const setEmployeeRole = (id: number, role_id: number) =>
  request<Employee>(`/admin/employees/${id}/role`, {
    method: 'POST',
    body: JSON.stringify({ role_id }),
  });

export const setEmployeeStatus = (id: number, status: EmployeeStatus) =>
  request<Employee>(`/admin/employees/${id}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  });

export interface RoleInput {
  code: string;
  name_uz: string;
  name_ru: string;
  icon: string;
  kind: RoleKind;
  template_ids: number[];
}

// --- E'lonlar (faqat admin) ---

/** Matn XOM yuboriladi — HTML escape serverda, botga uzatishda qilinadi. */
export const sendBroadcast = (body: string) =>
  request<Broadcast>('/admin/broadcasts', { method: 'POST', body: JSON.stringify({ body }) });

export const listBroadcasts = (limit = 20) =>
  request<Broadcast[]>(`/admin/broadcasts?limit=${limit}`);

export const createRole = (payload: RoleInput) =>
  request<{ id: number; code: string }>('/admin/roles', {
    method: 'POST',
    body: JSON.stringify(payload),
  });

export const updateRole = (id: number, payload: Partial<RoleInput>) =>
  request<{ id: number; code: string }>(`/admin/roles/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
