/** API tiplari — backend `app/api/v1/schemas.py` bilan mos. */

export type Lang = 'uz' | 'ru';
export type RoleKind = 'reporter' | 'admin' | 'accountant';

export type SubmissionStatus =
  | 'draft'
  | 'submitted'
  | 'in_review'
  | 'price_negotiation'
  | 'price_disputed'
  | 'reopened'
  | 'approved'
  | 'rejected'
  | 'paid';

export interface Role {
  code: string;
  name: string;
  kind: RoleKind;
  icon: string;
}

export type EmployeeStatus = 'active' | 'blocked' | 'fired';

export interface Employee {
  id: number;
  full_name: string;
  phone: string;
  lang: Lang;
  role: Role;
  role_id: number;
  workshop_name: string | null;
  status: EmployeeStatus;
  /** Xodim botga `/start` bosib telefonini yuborganmi. */
  tg_linked: boolean;
}

export interface TemplateInfo {
  id: number;
  code: string;
  name: string;
  icon: string;
  version: number;
  has_money: boolean;
  negotiable: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  employee: Employee;
  templates: TemplateInfo[];
}

export interface Vehicle {
  id: number;
  plate_number: string;
  plate_display: string;
  brand: string;
  model: string;
  year: number | null;
  status: string;
  odometer_km: number | null;
  current_driver_name?: string | null;
}

export interface Line {
  id: number;
  kind: 'labor' | 'part';
  name: string;
  qty: number;
  proposed_amount: number;
  approved_amount: number | null;
  price_change_reason: string | null;
  mechanic_accepted_at: string | null;
  mechanic_accept_mode: string | null;
}

export interface MediaItem {
  id: number;
  field_code: string | null;
  kind: string;
  mime: string;
  url: string;
}

export interface Submission {
  id: number;
  number: string;
  status: SubmissionStatus;
  template_code: string;
  template_version: number;
  author_id: number;
  author_name: string;
  vehicle: Vehicle | null;
  data: Record<string, unknown>;
  proposed_labor_amount: number;
  labor_amount: number | null;
  parts_amount: number;
  total_amount: number;
  auto_approved: boolean;
  price_negotiated: boolean;
  arrived_at: string | null;
  left_at: string | null;
  submitted_at: string | null;
  downtime_seconds: number | null;
  lines: Line[];
  media: MediaItem[];
}

export interface FieldSchema {
  code: string;
  type: string;
  label: { uz: string; ru?: string };
  hint?: { uz?: string; ru?: string };
  required: boolean;
  section?: string | null;
  options?: Record<string, unknown>;
  validation?: Record<string, unknown>;
}

export interface TemplateSchema {
  code: string;
  version: number;
  name: { uz: string; ru?: string };
  sections?: { code: string; title: { uz: string; ru?: string } }[];
  field_mapping?: Record<string, string>;
  fields: FieldSchema[];
}

export interface PriceContext {
  line_id: number;
  name: string;
  proposed_amount: number;
  count: number;
  avg_approved: number | null;
  min_approved: number | null;
  max_approved: number | null;
  author_avg: number | null;
  author_reduction_pct: number | null;
  quick_amounts: number[];
}

export interface PriceStats {
  lines_total: number;
  lines_reduced: number;
  proposed_total: number;
  approved_total: number;
  reduction_total: number;
  reduction_rate_pct: number;
  avg_reduction_pct: number;
  disputes: number;
}

export interface Dashboard {
  period: string;
  total_submissions: number;
  approved_count: number;
  proposed_total: number;
  approved_total: number;
  parts_total: number;
  saved: number;
  saved_pct: number;
  auto_approved_count: number;
  auto_approved_total: number;
  pending_review: number;
  in_negotiation: number;
  vehicles_in_service: number;
}

export interface WorkCatalogItem {
  id: number;
  code: string;
  name: string;
  category: string | null;
  /** ⚠️ `reporter` uchun doim null — server chiqarib tashlaydi (R3). */
  reference_price: number | null;
}

export interface ApiErrorBody {
  error: { code: string; message: string; fields?: Record<string, string> };
}

// --- Konstruktorlar (Faza 2) -------------------------------------------------

/** Mini App va bot chiza oladigan maydon turlari (backend: `engine.SUPPORTED_TYPES`). */
export const FIELD_TYPES = [
  'text',
  'textarea',
  'number',
  'money',
  'bool',
  'select',
  'photo',
  'vehicle_picker',
  'submission_picker',
  'lines',
  'geo',
] as const;

export type FieldType = (typeof FIELD_TYPES)[number];

export interface FieldDefinition {
  code: string;
  type: FieldType;
  label: { uz: string; ru?: string };
  hint?: { uz?: string; ru?: string } | null;
  required?: boolean;
  section?: string | null;
  sort?: number;
  options?: Record<string, unknown>;
  validation?: Record<string, unknown>;
  visible_if?: Record<string, unknown> | null;
}

export interface TemplateDefinition {
  code: string;
  name: { uz: string; ru?: string };
  icon: string;
  subject_type: 'vehicle' | 'employee' | 'none';
  has_money: boolean;
  negotiable: boolean;
  version?: number;
  field_mapping: Record<string, string>;
  sections: { code: string; title: { uz: string; ru?: string } }[];
  fields: FieldDefinition[];
}

export interface TemplateSummary {
  id: number;
  code: string;
  name_uz: string;
  name_ru: string;
  icon: string;
  version: number;
  published_version: number | null;
  is_draft: boolean;
  is_active: boolean;
  has_money: boolean;
  negotiable: boolean;
  fields_count: number;
}

export interface TemplateDetail extends TemplateSummary {
  definition: TemplateDefinition;
}

export interface RoleSummary {
  id: number;
  code: string;
  name_uz: string;
  name_ru: string;
  icon: string;
  kind: RoleKind;
  is_system: boolean;
  template_ids: number[];
}

/** `submission_picker` nomzodi — summa yo'q (backend: `LinkableSubmissionOut`). */
export interface LinkableSubmission {
  id: number;
  number: string;
  status: SubmissionStatus;
  template_code: string;
  author_name: string;
  vehicle_plate: string | null;
  submitted_at: string | null;
}

// --- Davr va to'lovlar (admin/buxgalter) -------------------------------------

export interface Period {
  id: number;
  year: number;
  month: number;
  status: 'open' | 'locking' | 'closed';
  closed_at: string | null;
}

export interface Precheck {
  can_close: boolean;
  /** `[{code, params}]` — i18n kaliti va o'rniga qo'yiladigan qiymatlar. */
  blockers: Record<string, unknown>[];
  warnings: Record<string, unknown>[];
}

export interface Payout {
  id: number;
  employee_id: number;
  employee_name: string;
  submissions_count: number;
  proposed_total: number;
  labor_total: number;
  reduction_total: number;
  bonus: number;
  penalty: number;
  total: number;
  status: 'draft' | 'approved' | 'paid';
}

export type ExportKind = 'submissions' | 'payouts' | 'savings';

// --- E'lonlar (faqat admin) --------------------------------------------------

/** Admin e'loni — bot orqali barcha faol, botga bog'langan xodimlarga boradi.
 *
 * Yetkazish hisobi (`delivered/failed/pending`) faqat tarix ro'yxatida keladi:
 * yuborish javobida navbat endi to'lgan bo'ladi, sanashning ma'nosi yo'q.
 * `body` — XOM matn (HTML escape serverda, faqat botga yuborishda qilinadi).
 */
export interface Broadcast {
  id: number;
  body: string;
  recipients_total: number;
  created_at: string;
  author_name: string;
  delivered?: number;
  failed?: number;
  pending?: number;
}
