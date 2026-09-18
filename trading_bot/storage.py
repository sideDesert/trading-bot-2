import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

IST = ZoneInfo("Asia/Kolkata")

ALLOWED_TABLES = frozenset({"market_data", "model_advice", "trade_feedback"})

_MARKET_DATA_COLUMNS = (
    "time",
    "nifty_price",
    "india_vix",
    "expiry_date",
    "atm_strike",
    "atm_call_instrument_key",
    "atm_put_instrument_key",
    "atm_call_price",
    "atm_put_price",
    "iv_percentile",
    "pcr",
    "relative_volume",
    "vwap_position",
    "opening_range_state",
    "call_oi_wall",
    "put_oi_wall",
    "spread",
    "source_age_seconds",
    "chain_age_seconds",
    "data_is_stale",
    "trading_is_blocked",
    "block_reason",
    "bar_time",
    "spot_bar_open",
    "spot_bar_high",
    "spot_bar_low",
    "spot_bar_close",
    "future_bar_open",
    "future_bar_high",
    "future_bar_low",
    "future_bar_close",
    "future_bar_volume",
    "nifty_future_price",
    "lot_size",
    "session_state",
    "is_expiry_day",
    "minutes_to_derivatives_close",
    "synthetic_fwd_basis",
    "atm_iv",
    "atm_expected_move",
    "opening_straddle",
    "expected_move_consumed_pct",
    "realized_vol_10d",
    "vrp_ratio",
    "opening_range_high",
    "opening_range_low",
    "opening_range_width",
    "narrow_range_threshold",
    "opening_range_is_narrow",
    "relative_volume_spike",
    "futures_vwap",
    "vwap_sigma",
    "first_30m_return_pct",
    "call_oi_walls",
    "put_oi_walls",
    "local_gex",
    "local_gex_sign",
    "momentum_reversion_selector",
    "gate_reasons",
    "gate_warnings",
    "shadow_candidate",
    "bar_age_seconds",
    "captured_at",
    "chain_window",
    "tod_median_30m_range",
    "daily_net_pnl",
    "daily_pnl_costed_trades",
    "daily_pnl_uncosted_trades",
    "expected_mfe_per_unit",
    "calibration_sample_size",
    "calibrated_mae_p90",
)

_NEW_COLUMNS = (
    ("bar_time", "TIMESTAMPTZ"),
    ("spot_bar_open", "DOUBLE"),
    ("spot_bar_high", "DOUBLE"),
    ("spot_bar_low", "DOUBLE"),
    ("spot_bar_close", "DOUBLE"),
    ("future_bar_open", "DOUBLE"),
    ("future_bar_high", "DOUBLE"),
    ("future_bar_low", "DOUBLE"),
    ("future_bar_close", "DOUBLE"),
    ("future_bar_volume", "DOUBLE"),
    ("nifty_future_price", "DOUBLE"),
    ("lot_size", "INTEGER"),
    ("session_state", "VARCHAR"),
    ("is_expiry_day", "BOOLEAN"),
    ("minutes_to_derivatives_close", "INTEGER"),
    ("synthetic_fwd_basis", "DOUBLE"),
    ("atm_iv", "DOUBLE"),
    ("atm_expected_move", "DOUBLE"),
    ("opening_straddle", "DOUBLE"),
    ("expected_move_consumed_pct", "DOUBLE"),
    ("realized_vol_10d", "DOUBLE"),
    ("vrp_ratio", "DOUBLE"),
    ("opening_range_high", "DOUBLE"),
    ("opening_range_low", "DOUBLE"),
    ("opening_range_width", "DOUBLE"),
    ("narrow_range_threshold", "DOUBLE"),
    ("opening_range_is_narrow", "BOOLEAN"),
    ("relative_volume_spike", "BOOLEAN"),
    ("futures_vwap", "DOUBLE"),
    ("vwap_sigma", "DOUBLE"),
    ("first_30m_return_pct", "DOUBLE"),
    ("call_oi_walls", "JSON"),
    ("put_oi_walls", "JSON"),
    ("local_gex", "DOUBLE"),
    ("local_gex_sign", "VARCHAR"),
    ("momentum_reversion_selector", "VARCHAR"),
    ("gate_reasons", "JSON"),
    ("gate_warnings", "JSON"),
    ("shadow_candidate", "JSON"),
    ("bar_age_seconds", "DOUBLE"),
    ("captured_at", "TIMESTAMPTZ"),
    ("chain_window", "JSON"),
    ("tod_median_30m_range", "DOUBLE"),
    ("daily_net_pnl", "DOUBLE"),
    ("daily_pnl_costed_trades", "INTEGER"),
    ("daily_pnl_uncosted_trades", "INTEGER"),
    ("expected_mfe_per_unit", "DOUBLE"),
    ("calibration_sample_size", "INTEGER"),
    ("calibrated_mae_p90", "DOUBLE"),
)

_FEEDBACK_NEW_COLUMNS = (
    ("evaluation_mode", "VARCHAR"),
    ("price_basis", "VARCHAR"),
    ("result_status", "VARCHAR"),
    ("lot_size", "INTEGER"),
    ("quoted_spread", "DOUBLE"),
    ("excursion_source", "VARCHAR"),
)

_ADVICE_NEW_COLUMNS = (
    ("exact_model_output_raw", "VARCHAR"),
    ("source", "VARCHAR"),
    ("instrument_key", "VARCHAR"),
    ("strike", "DOUBLE"),
    ("prompt_hash", "VARCHAR"),
    ("latency_ms", "DOUBLE"),
    ("fallback_reason", "VARCHAR"),
    ("validation_events", "JSON"),
    ("reask_used", "BOOLEAN"),
    ("hallucination_event", "BOOLEAN"),
)

_MIGRATIONS = tuple(
    f"ALTER TABLE market_data ADD COLUMN IF NOT EXISTS {name} {kind}"
    for name, kind in _NEW_COLUMNS
) + tuple(
    f"ALTER TABLE model_advice ADD COLUMN IF NOT EXISTS {name} {kind}"
    for name, kind in _ADVICE_NEW_COLUMNS
) + tuple(
    f"ALTER TABLE trade_feedback ADD COLUMN IF NOT EXISTS {name} {kind}"
    for name, kind in _FEEDBACK_NEW_COLUMNS
)

_ADVICE_MIGRATION_MODEL_ATTEMPTS = (
    "ALTER TABLE model_advice ADD COLUMN IF NOT EXISTS "
    "model_attempts JSON NOT NULL DEFAULT '[]'"
)

_ADVICE_MIGRATION_MODEL_ATTEMPTS_BACKFILL = (
    "UPDATE model_advice SET model_attempts = '[]' "
    "WHERE model_attempts IS NULL"
)

_MODEL_ADVICE_COLUMNS = (
    "advice_id",
    "advice_at",
    "context_from",
    "context_to",
    "prompt_version",
    "model_name",
    "action",
    "confidence",
    "setup_quality",
    "entry_price",
    "stop_price",
    "target_price",
    "idea_fails_if",
    "data_conflict",
    "reason",
    "exact_model_input",
    "exact_model_output",
    "exact_model_output_raw",
    "source",
    "instrument_key",
    "strike",
    "prompt_hash",
    "latency_ms",
    "fallback_reason",
    "validation_events",
    "reask_used",
    "hallucination_event",
    "model_attempts",
)

_ADVICE_TIMESTAMP_COLUMNS = ("advice_at", "context_from", "context_to")

_FEEDBACK_COLUMNS = (
    "advice_id",
    "feedback_at",
    "trade_was_taken",
    "entered_at",
    "exited_at",
    "actual_entry_price",
    "actual_exit_price",
    "lots",
    "user_verdict",
    "mae",
    "mfe",
    "user_notes",
    "evaluation_mode",
    "price_basis",
    "result_status",
    "lot_size",
    "quoted_spread",
    "excursion_source",
)

_FEEDBACK_TIMESTAMP_COLUMNS = ("feedback_at", "entered_at", "exited_at")

EVALUATION_MODES = frozenset({"USER", "SHADOW_30M"})

_TRADE_FEEDBACK_DDL = """
    CREATE TABLE IF NOT EXISTS trade_feedback (
      advice_id VARCHAR NOT NULL REFERENCES model_advice(advice_id),
      feedback_at TIMESTAMPTZ NOT NULL,
      trade_was_taken BOOLEAN NOT NULL,
      entered_at TIMESTAMPTZ,
      exited_at TIMESTAMPTZ,
      actual_entry_price DOUBLE,
      actual_exit_price DOUBLE,
      lots INTEGER,
      user_verdict VARCHAR NOT NULL CHECK (user_verdict IN ('WORKED','DID_NOT_WORK','NOT_TAKEN')),
      mae DOUBLE,
      mfe DOUBLE,
      user_notes VARCHAR,
      evaluation_mode VARCHAR NOT NULL CHECK (evaluation_mode IN ('USER','SHADOW_30M')),
      price_basis VARCHAR CHECK (price_basis IN ('ACTUAL_FILL','SHADOW_QUOTE_MODEL')),
      result_status VARCHAR CHECK (result_status IN ('USER_RECORDED','NOT_TAKEN','STOP_HIT','TARGET_HIT','STOP_HIT_AMBIGUOUS','HORIZON_EXIT','MISSING_DATA')),
      lot_size INTEGER,
      quoted_spread DOUBLE,
      excursion_source VARCHAR CHECK (excursion_source IN ('OPTION_1M_LTP_PROXY','USER_PROVIDED','UNAVAILABLE')),
      PRIMARY KEY (advice_id, evaluation_mode)
    )
    """

# Legacy rows can predate the evaluation_mode column. Every field this
# backfill reads (trade_was_taken, user_verdict, entered_at,
# actual_entry_price, mae) already existed in the oldest supported schema,
# and legacy single-primary-key tables hold at most one row per advice_id,
# so the backfilled (advice_id, evaluation_mode) pairs cannot collide.
_TRADE_FEEDBACK_MODE_BACKFILL = """
    CASE
      WHEN evaluation_mode IN ('USER', 'SHADOW_30M') THEN evaluation_mode
      WHEN trade_was_taken THEN 'USER'
      WHEN user_verdict IN ('WORKED', 'DID_NOT_WORK') THEN 'USER'
      WHEN entered_at IS NOT NULL
        OR actual_entry_price IS NOT NULL
        OR mae IS NOT NULL THEN 'SHADOW_30M'
      ELSE 'USER'
    END
    """


@dataclass(frozen=True)
class MarketDataRow:
    time: datetime
    nifty_price: "float | None"
    india_vix: "float | None"
    expiry_date: date
    atm_strike: float
    atm_call_instrument_key: str
    atm_put_instrument_key: str
    atm_call_price: "float | None"
    atm_put_price: "float | None"
    iv_percentile: "float | None" = None
    pcr: "float | None" = None
    relative_volume: "float | None" = None
    vwap_position: "str | None" = None
    opening_range_state: "str | None" = None
    call_oi_wall: "float | None" = None
    put_oi_wall: "float | None" = None
    spread: "float | None" = None
    source_age_seconds: "float | None" = None
    chain_age_seconds: "float | None" = None
    data_is_stale: bool = True
    trading_is_blocked: bool = True
    block_reason: str = "FEATURE_ENGINE_NOT_IMPLEMENTED"
    bar_time: "datetime | None" = None
    spot_bar_open: "float | None" = None
    spot_bar_high: "float | None" = None
    spot_bar_low: "float | None" = None
    spot_bar_close: "float | None" = None
    future_bar_open: "float | None" = None
    future_bar_high: "float | None" = None
    future_bar_low: "float | None" = None
    future_bar_close: "float | None" = None
    future_bar_volume: "float | None" = None
    nifty_future_price: "float | None" = None
    lot_size: "int | None" = None
    session_state: "str | None" = None
    is_expiry_day: "bool | None" = None
    minutes_to_derivatives_close: "int | None" = None
    synthetic_fwd_basis: "float | None" = None
    atm_iv: "float | None" = None
    atm_expected_move: "float | None" = None
    opening_straddle: "float | None" = None
    expected_move_consumed_pct: "float | None" = None
    realized_vol_10d: "float | None" = None
    vrp_ratio: "float | None" = None
    opening_range_high: "float | None" = None
    opening_range_low: "float | None" = None
    opening_range_width: "float | None" = None
    narrow_range_threshold: "float | None" = None
    opening_range_is_narrow: "bool | None" = None
    relative_volume_spike: "bool | None" = None
    futures_vwap: "float | None" = None
    vwap_sigma: "float | None" = None
    first_30m_return_pct: "float | None" = None
    call_oi_walls: "str | None" = None
    put_oi_walls: "str | None" = None
    local_gex: "float | None" = None
    local_gex_sign: "str | None" = None
    momentum_reversion_selector: "str | None" = None
    gate_reasons: "str | None" = None
    gate_warnings: "str | None" = None
    shadow_candidate: "str | None" = None
    bar_age_seconds: "float | None" = None
    captured_at: "datetime | None" = None
    chain_window: "str | None" = None
    tod_median_30m_range: "float | None" = None
    daily_net_pnl: "float | None" = None
    daily_pnl_costed_trades: "int | None" = None
    daily_pnl_uncosted_trades: "int | None" = None
    expected_mfe_per_unit: "float | None" = None
    calibration_sample_size: "int | None" = None
    calibrated_mae_p90: "float | None" = None


@dataclass(frozen=True)
class ModelAdviceRow:
    advice_id: str
    advice_at: datetime
    context_from: datetime
    context_to: datetime
    prompt_version: str
    model_name: str
    action: str
    confidence: float
    setup_quality: str
    entry_price: "float | None"
    stop_price: "float | None"
    target_price: "float | None"
    idea_fails_if: str
    data_conflict: bool
    reason: str
    exact_model_input: str
    exact_model_output: str
    source: "str | None" = None
    instrument_key: "str | None" = None
    strike: "float | None" = None
    prompt_hash: "str | None" = None
    latency_ms: "float | None" = None
    fallback_reason: "str | None" = None
    validation_events: "str | None" = None
    reask_used: "bool | None" = None
    hallucination_event: "bool | None" = None
    model_attempts: str = "[]"
    exact_model_output_raw: "str | None" = None


@dataclass(frozen=True)
class TradeFeedbackRow:
    advice_id: str
    feedback_at: datetime
    trade_was_taken: bool
    entered_at: "datetime | None"
    exited_at: "datetime | None"
    actual_entry_price: "float | None"
    actual_exit_price: "float | None"
    lots: "int | None"
    user_verdict: str
    mae: "float | None"
    mfe: "float | None"
    user_notes: "str | None"
    evaluation_mode: str = "USER"
    price_basis: str = "ACTUAL_FILL"
    result_status: str = "USER_RECORDED"
    lot_size: "int | None" = None
    quoted_spread: "float | None" = None
    excursion_source: str = "UNAVAILABLE"


_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS market_data (
      time TIMESTAMPTZ PRIMARY KEY,
      nifty_price DOUBLE,
      india_vix DOUBLE,
      expiry_date DATE NOT NULL,
      atm_strike DOUBLE NOT NULL,
      atm_call_instrument_key VARCHAR NOT NULL,
      atm_put_instrument_key VARCHAR NOT NULL,
      atm_call_price DOUBLE,
      atm_put_price DOUBLE,
      iv_percentile DOUBLE,
      pcr DOUBLE,
      relative_volume DOUBLE,
      vwap_position VARCHAR,
      opening_range_state VARCHAR,
      call_oi_wall DOUBLE,
      put_oi_wall DOUBLE,
      spread DOUBLE,
      source_age_seconds DOUBLE,
      chain_age_seconds DOUBLE,
      data_is_stale BOOLEAN NOT NULL,
      trading_is_blocked BOOLEAN NOT NULL,
      block_reason VARCHAR NOT NULL,
      bar_time TIMESTAMPTZ,
      spot_bar_open DOUBLE,
      spot_bar_high DOUBLE,
      spot_bar_low DOUBLE,
      spot_bar_close DOUBLE,
      future_bar_open DOUBLE,
      future_bar_high DOUBLE,
      future_bar_low DOUBLE,
      future_bar_close DOUBLE,
      future_bar_volume DOUBLE,
      nifty_future_price DOUBLE,
      lot_size INTEGER,
      session_state VARCHAR,
      is_expiry_day BOOLEAN,
      minutes_to_derivatives_close INTEGER,
      synthetic_fwd_basis DOUBLE,
      atm_iv DOUBLE,
      atm_expected_move DOUBLE,
      opening_straddle DOUBLE,
      expected_move_consumed_pct DOUBLE,
      realized_vol_10d DOUBLE,
      vrp_ratio DOUBLE,
      opening_range_high DOUBLE,
      opening_range_low DOUBLE,
      opening_range_width DOUBLE,
      narrow_range_threshold DOUBLE,
      opening_range_is_narrow BOOLEAN,
      relative_volume_spike BOOLEAN,
      futures_vwap DOUBLE,
      vwap_sigma DOUBLE,
      first_30m_return_pct DOUBLE,
      call_oi_walls JSON,
      put_oi_walls JSON,
      local_gex DOUBLE,
      local_gex_sign VARCHAR,
      momentum_reversion_selector VARCHAR,
      gate_reasons JSON,
      gate_warnings JSON,
      shadow_candidate JSON,
      bar_age_seconds DOUBLE,
      captured_at TIMESTAMPTZ,
      chain_window JSON,
      tod_median_30m_range DOUBLE,
      daily_net_pnl DOUBLE,
      daily_pnl_costed_trades INTEGER,
      daily_pnl_uncosted_trades INTEGER,
      expected_mfe_per_unit DOUBLE,
      calibration_sample_size INTEGER,
      calibrated_mae_p90 DOUBLE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS model_advice (
      advice_id VARCHAR PRIMARY KEY,
      advice_at TIMESTAMPTZ NOT NULL,
      context_from TIMESTAMPTZ NOT NULL,
      context_to TIMESTAMPTZ NOT NULL,
      prompt_version VARCHAR NOT NULL,
      model_name VARCHAR NOT NULL,
      action VARCHAR NOT NULL CHECK (action IN ('LONG_CALL','LONG_PUT','NO_TRADE')),
      confidence DOUBLE NOT NULL,
      setup_quality VARCHAR NOT NULL CHECK (setup_quality IN ('A','B','C')),
      entry_price DOUBLE,
      stop_price DOUBLE,
      target_price DOUBLE,
      idea_fails_if VARCHAR NOT NULL,
      data_conflict BOOLEAN NOT NULL,
      reason VARCHAR NOT NULL,
      exact_model_input JSON NOT NULL,
      exact_model_output VARCHAR NOT NULL,
      exact_model_output_raw VARCHAR,
      source VARCHAR,
      instrument_key VARCHAR,
      strike DOUBLE,
      prompt_hash VARCHAR,
      latency_ms DOUBLE,
      fallback_reason VARCHAR,
      validation_events JSON,
      reask_used BOOLEAN,
      hallucination_event BOOLEAN,
      model_attempts JSON NOT NULL DEFAULT '[]'
    )
    """,
    _TRADE_FEEDBACK_DDL,
)


class DuckDBStore:
    def __init__(self, path) -> None:
        self._path = Path(path)
        self._conn = None
        self._legacy_output_json = False
        self._advice_context_unique = False

    def __enter__(self) -> "DuckDBStore":
        return self.initialize()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def initialize(self) -> "DuckDBStore":
        if self._conn is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self._path))
            for statement in _SCHEMA:
                self._conn.execute(statement)
            for statement in _MIGRATIONS:
                self._conn.execute(statement)
            self._migrate_trade_feedback_key()
            try:
                self._conn.execute(_ADVICE_MIGRATION_MODEL_ATTEMPTS)
            except duckdb.Error:
                self._conn.execute(
                    "ALTER TABLE model_advice ADD COLUMN IF NOT EXISTS "
                    "model_attempts JSON"
                )
            self._conn.execute(_ADVICE_MIGRATION_MODEL_ATTEMPTS_BACKFILL)
            duplicate = self._conn.execute(
                "SELECT COUNT(*) FROM ("
                "SELECT epoch_ms(context_to) AS ct, prompt_hash "
                "FROM model_advice "
                "WHERE context_to IS NOT NULL AND prompt_hash IS NOT NULL "
                "GROUP BY ct, prompt_hash HAVING COUNT(*) > 1)"
            ).fetchone()[0] > 0
            if duplicate:
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS "
                    "model_advice_context_prompt_idx "
                    "ON model_advice(context_to, prompt_hash)"
                )
                self._advice_context_unique = False
            else:
                self._conn.execute(
                    "DROP INDEX IF EXISTS model_advice_context_prompt_idx"
                )
                self._conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "model_advice_context_prompt_idx "
                    "ON model_advice(context_to, prompt_hash)"
                )
                self._advice_context_unique = True
            info = self._conn.execute(
                "PRAGMA table_info('model_advice')"
            ).fetchall()
            self._legacy_output_json = any(
                record[1] == "exact_model_output" and record[2] == "JSON"
                for record in info
            )
        return self

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _migrate_trade_feedback_key(self) -> None:
        conn = self._connection()
        info = conn.execute(
            "PRAGMA table_info('trade_feedback')"
        ).fetchall()
        key_columns = {record[1] for record in info if record[5]}
        if key_columns == {"advice_id", "evaluation_mode"}:
            return
        migrated_ddl = _TRADE_FEEDBACK_DDL.replace(
            "CREATE TABLE IF NOT EXISTS trade_feedback",
            "CREATE TABLE trade_feedback_migrated",
        )
        columns = ", ".join(_FEEDBACK_COLUMNS)
        select_columns = ", ".join(
            _TRADE_FEEDBACK_MODE_BACKFILL.strip()
            if name == "evaluation_mode"
            else name
            for name in _FEEDBACK_COLUMNS
        )
        conn.execute("BEGIN TRANSACTION")
        try:
            conn.execute(migrated_ddl)
            conn.execute(
                f"INSERT INTO trade_feedback_migrated ({columns}) "
                f"SELECT {select_columns} FROM trade_feedback"
            )
            conn.execute("DROP TABLE trade_feedback")
            conn.execute(
                "ALTER TABLE trade_feedback_migrated "
                "RENAME TO trade_feedback"
            )
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")

    def upsert_market_data(self, row: MarketDataRow) -> None:
        conn = self._connection()
        columns = ", ".join(_MARKET_DATA_COLUMNS)
        placeholders = ", ".join("?" for _ in _MARKET_DATA_COLUMNS)
        values = [getattr(row, name) for name in _MARKET_DATA_COLUMNS]
        conn.execute(
            f"INSERT OR REPLACE INTO market_data ({columns}) "
            f"VALUES ({placeholders})",
            values,
        )

    _MARKET_DATA_TS_COLUMNS = ("time", "bar_time", "captured_at")

    def _market_data_select_columns(self):
        return ", ".join(
            f"epoch_ms({name}) AS {name}"
            if name in self._MARKET_DATA_TS_COLUMNS
            else name
            for name in _MARKET_DATA_COLUMNS
        )

    @staticmethod
    def _convert_market_row(names, record):
        row = dict(zip(names, record))
        for name in DuckDBStore._MARKET_DATA_TS_COLUMNS:
            if row[name] is not None:
                row[name] = datetime.fromtimestamp(
                    row[name] / 1000.0, tz=timezone.utc
                )
        return row

    def latest_market_data(self):
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._market_data_select_columns()} FROM market_data "
            "ORDER BY time DESC LIMIT 1"
        )
        record = cursor.fetchone()
        if record is None:
            return None
        return self._convert_market_row(
            [column[0] for column in cursor.description], record
        )

    def recent_market_data(self, limit: int = 15, through=None):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        conn = self._connection()
        query = (
            f"SELECT {self._market_data_select_columns()} FROM market_data"
        )
        params = []
        if through is not None:
            query += " WHERE time <= ?"
            params.append(through)
        query += " ORDER BY time DESC LIMIT ?"
        params.append(limit)
        cursor = conn.execute(query, params)
        names = [column[0] for column in cursor.description]
        rows = [
            self._convert_market_row(names, record)
            for record in cursor.fetchall()
        ]
        return list(reversed(rows))

    def atm_iv_history(self, before: datetime, limit: int = 252) -> "list[float]":
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if before.tzinfo is None:
            before_day = before.replace(tzinfo=IST).date()
        else:
            before_day = before.astimezone(IST).date()
        conn = self._connection()
        cursor = conn.execute(
            "SELECT epoch_ms(time) AS t, atm_iv FROM market_data "
            "WHERE time < ? AND atm_iv IS NOT NULL AND atm_iv > 0 "
            "ORDER BY t DESC",
            [before],
        )
        by_day = {}
        for epoch, iv in cursor.fetchall():
            day = datetime.fromtimestamp(
                epoch / 1000.0, tz=timezone.utc
            ).astimezone(IST).date()
            if day >= before_day:
                continue
            if day not in by_day:
                by_day[day] = float(iv)
        return [by_day[day] for day in sorted(by_day)][-limit:]

    def insert_model_advice(self, row: ModelAdviceRow) -> None:
        conn = self._connection()
        columns = ", ".join(_MODEL_ADVICE_COLUMNS)
        placeholders = ", ".join("?" for _ in _MODEL_ADVICE_COLUMNS)
        canonical_raw = (
            row.exact_model_output_raw
            if row.exact_model_output_raw is not None
            else row.exact_model_output
        )
        values = [getattr(row, name) for name in _MODEL_ADVICE_COLUMNS]
        output_index = _MODEL_ADVICE_COLUMNS.index("exact_model_output")
        values[output_index] = (
            json.dumps(canonical_raw)
            if self._legacy_output_json
            else canonical_raw
        )
        values[
            _MODEL_ADVICE_COLUMNS.index("exact_model_output_raw")
        ] = canonical_raw
        conn.execute(
            f"INSERT INTO model_advice ({columns}) VALUES ({placeholders})",
            values,
        )

    def _advice_select(self):
        return ", ".join(
            f"epoch_ms({name}) AS {name}"
            if name in _ADVICE_TIMESTAMP_COLUMNS
            else name
            for name in _MODEL_ADVICE_COLUMNS
        )

    def _convert_advice_row(self, names, record):
        row = dict(zip(names, record))
        for name in _ADVICE_TIMESTAMP_COLUMNS:
            if row[name] is not None:
                row[name] = datetime.fromtimestamp(
                    row[name] / 1000.0, tz=timezone.utc
                )
        raw_column = row.get("exact_model_output_raw")
        if raw_column is not None:
            row["exact_model_output"] = raw_column
        elif (
            self._legacy_output_json
            and row.get("exact_model_output") is not None
        ):
            try:
                parsed = json.loads(row["exact_model_output"])
            except ValueError:
                pass
            else:
                row["exact_model_output"] = (
                    parsed
                    if isinstance(parsed, str)
                    else json.dumps(
                        parsed, separators=(",", ":"), sort_keys=True
                    )
                )
        return row

    def get_model_advice(self, advice_id: str):
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._advice_select()} FROM model_advice "
            "WHERE advice_id = ?",
            [advice_id],
        )
        record = cursor.fetchone()
        if record is None:
            return None
        return self._convert_advice_row(
            [column[0] for column in cursor.description], record
        )

    def get_model_advice_for_context(
        self, context_to: datetime, prompt_hash: str
    ):
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._advice_select()} FROM model_advice "
            "WHERE context_to IS NOT DISTINCT FROM ? "
            "AND prompt_hash = ? "
            "ORDER BY advice_at DESC LIMIT 1",
            [context_to, prompt_hash],
        )
        record = cursor.fetchone()
        if record is None:
            return None
        return self._convert_advice_row(
            [column[0] for column in cursor.description], record
        )

    def model_advice_exists(self, context_to: datetime, prompt_hash: str) -> bool:
        if not isinstance(prompt_hash, str) or not prompt_hash.strip():
            raise ValueError("prompt_hash must be a non-empty string")
        conn = self._connection()
        record = conn.execute(
            "SELECT 1 FROM model_advice "
            "WHERE context_to = ? AND prompt_hash = ? LIMIT 1",
            [context_to, prompt_hash],
        ).fetchone()
        return record is not None

    def recent_model_advice(self, limit: int = 100):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._advice_select()} FROM model_advice "
            "ORDER BY advice_at DESC LIMIT ?",
            [limit],
        )
        names = [column[0] for column in cursor.description]
        return [
            self._convert_advice_row(names, record)
            for record in cursor.fetchall()
        ]

    def market_data_at(self, time: datetime):
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._market_data_select_columns()} FROM market_data "
            "WHERE time = ?",
            [time],
        )
        record = cursor.fetchone()
        if record is None:
            return None
        return self._convert_market_row(
            [column[0] for column in cursor.description], record
        )

    def insert_trade_feedback(self, row: TradeFeedbackRow) -> None:
        conn = self._connection()
        columns = ", ".join(_FEEDBACK_COLUMNS)
        placeholders = ", ".join("?" for _ in _FEEDBACK_COLUMNS)
        values = [getattr(row, name) for name in _FEEDBACK_COLUMNS]
        conn.execute(
            f"INSERT INTO trade_feedback ({columns}) VALUES ({placeholders})",
            values,
        )

    def _feedback_select(self):
        return ", ".join(
            f"epoch_ms({name}) AS {name}"
            if name in _FEEDBACK_TIMESTAMP_COLUMNS
            else name
            for name in _FEEDBACK_COLUMNS
        )

    @staticmethod
    def _convert_timestamps(row, names):
        for name in names:
            if row.get(name) is not None and isinstance(
                row[name], (int, float)
            ):
                row[name] = datetime.fromtimestamp(
                    row[name] / 1000.0, tz=timezone.utc
                )
        return row

    def get_trade_feedback(self, advice_id: str, evaluation_mode: str):
        if evaluation_mode not in EVALUATION_MODES:
            raise ValueError(
                f"evaluation_mode must be one of {sorted(EVALUATION_MODES)}"
            )
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._feedback_select()} FROM trade_feedback "
            "WHERE advice_id = ? AND evaluation_mode = ?",
            [advice_id, evaluation_mode],
        )
        record = cursor.fetchone()
        if record is None:
            return None
        return self._convert_timestamps(
            dict(zip([c[0] for c in cursor.description], record)),
            _FEEDBACK_TIMESTAMP_COLUMNS,
        )

    def get_trade_feedback_rows(self, advice_id: str):
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._feedback_select()} FROM trade_feedback "
            "WHERE advice_id = ? ORDER BY feedback_at DESC",
            [advice_id],
        )
        names = [column[0] for column in cursor.description]
        return [
            self._convert_timestamps(
                dict(zip(names, record)), _FEEDBACK_TIMESTAMP_COLUMNS
            )
            for record in cursor.fetchall()
        ]

    def recent_trade_feedback(self, limit: int = 100):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        conn = self._connection()
        cursor = conn.execute(
            f"SELECT {self._feedback_select()} FROM trade_feedback "
            "ORDER BY feedback_at DESC LIMIT ?",
            [limit],
        )
        names = [column[0] for column in cursor.description]
        return [
            self._convert_timestamps(
                dict(zip(names, record)), _FEEDBACK_TIMESTAMP_COLUMNS
            )
            for record in cursor.fetchall()
        ]

    def pending_shadow_advice(self, cutoff: datetime, limit: int = 20):
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        conn = self._connection()
        advice_cols = ", ".join(
            f"epoch_ms(a.{name}) AS {name}"
            if name in _ADVICE_TIMESTAMP_COLUMNS
            else f"a.{name}"
            for name in _MODEL_ADVICE_COLUMNS
        )
        cursor = conn.execute(
            f"""
            SELECT {advice_cols}, m.lot_size AS market_lot_size,
                   m.shadow_candidate AS market_shadow_candidate,
                   m.session_state AS market_session_state,
                   m.is_expiry_day AS market_is_expiry_day,
                   m.gate_reasons AS market_gate_reasons
            FROM model_advice a
            JOIN market_data m ON m.time = a.context_to
            LEFT JOIN trade_feedback f ON f.advice_id = a.advice_id
              AND f.evaluation_mode = 'SHADOW_30M'
            WHERE f.advice_id IS NULL AND a.source = 'shadow'
              AND a.action IN ('LONG_CALL','LONG_PUT') AND a.advice_at <= ?
            ORDER BY a.advice_at ASC LIMIT ?
            """,
            [cutoff, limit],
        )
        names = [column[0] for column in cursor.description]
        rows = []
        for record in cursor.fetchall():
            row = dict(zip(names, record))
            self._convert_timestamps(row, _ADVICE_TIMESTAMP_COLUMNS)
            raw_column = row.get("exact_model_output_raw")
            if raw_column is not None:
                row["exact_model_output"] = raw_column
            rows.append(row)
        return rows

    def evaluation_rows(self):
        conn = self._connection()
        feedback_cols = ", ".join(
            f"epoch_ms(f.{name}) AS {name}"
            if name in _FEEDBACK_TIMESTAMP_COLUMNS
            else f"f.{name}"
            for name in _FEEDBACK_COLUMNS
        )
        cursor = conn.execute(
            f"""
            SELECT {feedback_cols}, epoch_ms(a.advice_at) AS advice_at,
                   epoch_ms(a.context_to) AS context_to, a.prompt_version,
                   a.model_name, a.action, a.setup_quality, a.fallback_reason,
                   a.instrument_key, a.strike,
                   m.session_state AS market_session_state,
                   m.is_expiry_day AS market_is_expiry_day,
                   m.local_gex_sign AS market_local_gex_sign,
                   m.vwap_position AS market_vwap_position,
                   m.relative_volume AS market_relative_volume
            FROM trade_feedback f
            JOIN model_advice a ON a.advice_id = f.advice_id
            JOIN market_data m ON m.time = a.context_to
            ORDER BY a.advice_at ASC
            """
        )
        names = [column[0] for column in cursor.description]
        rows = []
        for record in cursor.fetchall():
            row = dict(zip(names, record))
            self._convert_timestamps(
                row,
                (
                    "feedback_at",
                    "entered_at",
                    "exited_at",
                    "advice_at",
                    "context_to",
                ),
            )
            rows.append(row)
        return rows

    def count(self, table_name: str) -> int:
        if table_name not in ALLOWED_TABLES:
            raise ValueError(f"table not allowed: {table_name!r}")
        conn = self._connection()
        return conn.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]

    def _connection(self):
        if self._conn is None:
            raise RuntimeError("store is not initialized")
        return self._conn
