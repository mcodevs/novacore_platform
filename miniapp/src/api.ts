/** API klient: initData → JWT, avtomatik refresh, qayta urinish (zaif internet). */

import { tg } from './telegram';
import { unwrap } from './unwrap';
import type {
  AuthResponse,
  Dashboard,
  Employee,
  EmployeeStatus,
  Lang,
  LinkableSubmission,
  MediaItem,
  PriceContext,
  PriceStats,
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
  const payload = text ? JSON.parse(text) : null;
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
    // tarmoq uzildi — bir marta qayta urinamiz
    if (!retry) throw new ApiError('network', 'Tarmoq bilan aloqa yo‘q');
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

export const disputePrice = (id: number, comment: string) =>
  request<Submission>(`/submissions/${id}/dispute-price`, {
    method: 'POST',
    body: JSON.stringify({ comment }),
  });

export const myPriceStats = () => request<PriceStats>('/me/price-stats');

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
