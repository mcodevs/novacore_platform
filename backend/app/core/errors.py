"""Domen xatolari — docs/02-architecture/04-api-design.md §10 dagi kodlar."""

from __future__ import annotations


class DomainError(Exception):
    """Barcha biznes xatolarining asosi."""

    code = "domain_error"
    http_status = 400

    def __init__(self, message: str = "", *, fields: dict[str, str] | None = None, **details):
        super().__init__(message or self.code)
        self.message = message or self.code
        self.fields = fields or {}
        self.details = details


class ValidationFailed(DomainError):
    code = "validation_failed"
    http_status = 400


class Unauthenticated(DomainError):
    code = "unauthenticated"
    http_status = 401


class InvalidInitData(DomainError):
    code = "invalid_init_data"
    http_status = 401


class Forbidden(DomainError):
    code = "forbidden"
    http_status = 403


class NotInRegistry(DomainError):
    code = "not_in_registry"
    http_status = 403


class PriceReferenceHidden(Forbidden):
    """R3 — tayanch narx `reporter` roliga API'da ham qaytarilmaydi."""

    code = "price_reference_hidden"
    http_status = 403


class NotFound(DomainError):
    code = "not_found"
    http_status = 404


class InvalidStateTransition(DomainError):
    code = "invalid_state_transition"
    http_status = 409


class SubmissionNotPayable(DomainError):
    """P1 — to'lov faqat `APPROVED` hisobotga qo'llanadi."""

    code = "submission_not_payable"
    http_status = 409


class PaymentAlreadyVoided(DomainError):
    """Bekor qilingan to'lovni qayta bekor qilib bo'lmaydi."""

    code = "payment_already_voided"
    http_status = 409


class SelfApprovalForbidden(DomainError):
    """R1 — approver_id ≠ author_id."""

    code = "self_approval_forbidden"
    http_status = 409


class LastAdminRequired(DomainError):
    """R8 — kamida bitta faol `kind='admin'` xodim bo'lishi shart."""

    code = "last_admin_required"
    http_status = 409


class FileTooLarge(DomainError):
    code = "file_too_large"
    http_status = 413


class PriceIncreaseForbidden(DomainError):
    """R2 — admin narxni faqat kamaytira oladi."""

    code = "price_increase_forbidden"
    http_status = 422


class BusinessRuleViolated(DomainError):
    code = "business_rule_violated"
    http_status = 422


class RateLimited(DomainError):
    code = "rate_limited"
    http_status = 429
