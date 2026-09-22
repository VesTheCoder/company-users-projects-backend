from time import perf_counter

import structlog
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram
from sqlalchemy import event


class Metrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        labels = ["route", "method", "status_class"]
        self.requests = Counter(
            "http_requests_total", "HTTP requests", labels, registry=self.registry
        )
        self.latency = Histogram(
            "http_request_duration_seconds",
            "HTTP latency",
            labels,
            registry=self.registry,
        )
        self.limiter_failures = Counter(
            "rate_limiter_failures_total",
            "Limiter dependency failures",
            registry=self.registry,
        )
        self.limiter_rejections = Counter(
            "rate_limit_rejections_total",
            "Rate limit rejections",
            registry=self.registry,
        )
        self.pool_timeouts = Counter(
            "db_pool_timeouts_total", "Pool checkout timeouts", registry=self.registry
        )
        self.pool_in_use = Gauge(
            "db_pool_in_use", "Checked out connections", registry=self.registry
        )
        self.pool_capacity = Gauge(
            "db_pool_capacity", "Maximum pool connections", registry=self.registry
        )
        self.slow_queries = Counter(
            "db_slow_queries_total", "Queries slower than 250ms", registry=self.registry
        )

    def instrument_engine(self, engine, capacity):
        self.pool_in_use.set_function(engine.pool.checkedout)
        self.pool_capacity.set(capacity)

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def before(connection, cursor, statement, parameters, context, executemany):
            context.query_started = perf_counter()

        @event.listens_for(engine.sync_engine, "after_cursor_execute")
        def after(connection, cursor, statement, parameters, context, executemany):
            duration = perf_counter() - context.query_started
            if duration > 0.25:
                self.slow_queries.inc()
                structlog.get_logger().warning(
                    "db.slow_query",
                    operation=statement.split()[0],
                    duration_ms=round(duration * 1000, 2),
                )
