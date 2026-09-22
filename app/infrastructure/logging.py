import logging

import structlog

SAFE_FIELDS = frozenset(
    {
        "timestamp",
        "level",
        "event",
        "service",
        "environment",
        "request_id",
        "correlation_id",
        "route",
        "method",
        "status_code",
        "duration_ms",
        "actor_user_id",
        "company_id",
        "operation",
        "error_type",
    }
)


def redact_log(logger, method, event):
    return {key: value for key, value in event.items() if key in SAFE_FIELDS}


def configure_logging(level: str):
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_log,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level)),
        logger_factory=structlog.PrintLoggerFactory(),
    )


def security_event(event, principal=None, company_id=None):
    fields = {}
    if principal:
        fields["actor_user_id"] = str(principal.user_id)
    if company_id:
        fields["company_id"] = str(company_id)
    structlog.get_logger().info(event, **fields)
