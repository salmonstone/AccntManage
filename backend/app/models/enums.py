from __future__ import annotations

import enum


class AccountPlatform(str, enum.Enum):
    BATTLENET = "battlenet"
    TWITCH = "twitch"


class AccountStatus(str, enum.Enum):
    DRAFT = "draft"
    LOCAL_RECORD_ONLY = "local_record_only"
    SIMULATED = "simulated"
    PENDING_EMAIL_VERIFICATION = "pending_email_verification"
    PENDING_PHONE_VERIFICATION = "pending_phone_verification"
    REGISTRATION_CONFIRMED = "registration_confirmed"
    EMAIL_UNVERIFIED = "email_unverified"
    VERIFIED = "verified"
    VERIFIED_LIVE = "verified_live"
    UNVERIFIED = "unverified"
    FAILED = "failed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    MOCKED = "mocked"
    MANUAL_REQUIRED = "manual_required"
    UNSUPPORTED = "unsupported"


class MailboxStatus(str, enum.Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    TOKEN_EXPIRED = "token_expired"
    REVOKED = "revoked"
    ERROR = "error"


class ProxyProtocol(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS4 = "socks4"
    SOCKS4A = "socks4a"
    SOCKS5 = "socks5"


class ProxyTestStatus(str, enum.Enum):
    UNTESTED = "untested"
    TESTING = "testing"
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    INTERRUPTED = "interrupted"


class JobType(str, enum.Enum):
    PROXY_TEST = "proxy_test"
    MAILBOX_VALIDATE = "mailbox_validate"
    MAILBOX_SEARCH = "mailbox_search"
    ACCOUNT_IMPORT = "account_import"
    ACCOUNT_SIMULATE = "account_simulate"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    BATTLENET_WORKFLOW = "battlenet_workflow"
    TWITCH_WORKFLOW = "twitch_workflow"


class ProviderType(str, enum.Enum):
    SMS = "sms"
    CAPTCHA = "captcha"
    MSGRAPH = "msgraph"


class ProviderStatus(str, enum.Enum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    CONFIGURED_NOT_TESTED = "configured_not_tested"
    LIVE_TESTED = "live_tested"
    MOCK_ONLY = "mock_only"
    CONNECTED = "connected"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class AuditAction(str, enum.Enum):
    SETTING_CHANGED = "setting_changed"
    PROVIDER_CONFIGURED = "provider_configured"
    MAILBOX_AUTHORIZED = "mailbox_authorized"
    MAILBOX_REVOKED = "mailbox_revoked"
    ACCOUNT_IMPORTED = "account_imported"
    ACCOUNT_DELETED = "account_deleted"
    BULK_DELETE = "bulk_delete"
    BACKUP_CREATED = "backup_created"
    BACKUP_RESTORED = "backup_restored"
    DATABASE_RESET = "database_reset"
    JOB_CANCELLED = "job_cancelled"
