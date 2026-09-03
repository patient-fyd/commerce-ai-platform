#!/usr/bin/env python3
"""Generate deterministic synthetic CommerceAI OLTP data as importable MySQL SQL."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import random
import tempfile
import time
from collections import Counter, defaultdict
from datetime import date, datetime, time as datetime_time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence, TextIO


SCALE_CONFIG = {
    "small": {
        "users": 1_000,
        "root_categories": 4,
        "leaf_categories": 16,
        "spus": 150,
        "skus": 400,
        "orders": 10_000,
    }
}

ORDER_PENDING = 10
ORDER_PAID = 20
ORDER_COMPLETED = 30
ORDER_CANCELLED = 40

PAYMENT_PENDING = 10
PAYMENT_SUCCEEDED = 20
PAYMENT_FAILED = 30
PAYMENT_CLOSED = 40

REFUND_PENDING = 10
REFUND_SUCCEEDED = 20
REFUND_FAILED = 30
REFUND_CANCELLED = 40
RESERVED_REFUND_STATUSES = {REFUND_PENDING, REFUND_SUCCEEDED}

PAYMENT_CHANNELS = ("WECHAT", "ALIPAY", "BANK_CARD")
PAYMENT_CHANNEL_WEIGHTS = (0.55, 0.30, 0.15)

BRANDS = ("Atlas", "BluePeak", "Cedar", "Lumen", "Northstar", "Orbit", "Willow")
PRODUCT_NOUNS = (
    "Phone", "Laptop", "Tablet", "Headphones", "Speaker", "Keyboard",
    "Mouse", "Monitor", "Camera", "Backpack", "Bottle", "Lamp",
    "Chair", "Notebook", "Router", "Watch", "Charger", "Kettle",
)
COLORS = ("Black", "White", "Blue", "Green", "Silver", "Sand")
SIZES = ("Compact", "Standard", "Plus", "Pro")
REFUND_REASONS = (
    "Synthetic: changed mind",
    "Synthetic: item did not fit",
    "Synthetic: duplicate purchase",
    "Synthetic: package issue",
    "Synthetic: product expectation mismatch",
)

Row = dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate deterministic synthetic CommerceAI data as MySQL INSERT SQL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--scale",
        choices=sorted(SCALE_CONFIG),
        default="small",
        help="dataset scale; only the local-development small scale is implemented",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument(
        "--start-date",
        type=iso_date,
        default=date(2026, 1, 1),
        help="inclusive business date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        type=iso_date,
        default=date(2026, 3, 31),
        help="inclusive business date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("source/data-generator/output/generated-data.sql"),
        help="output SQL file",
    )
    args = parser.parse_args()
    if args.end_date < args.start_date:
        parser.error("--end-date must be on or after --start-date")
    if args.output.exists() and args.output.is_dir():
        parser.error("--output must be a file path, not a directory")
    return args


def iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r}; expected YYYY-MM-DD"
        ) from exc


def format_datetime(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat(sep=" ", timespec="milliseconds")


def money(cents: int) -> Decimal:
    return Decimal(cents).scaleb(-2)


def random_after(
    rng: random.Random,
    base: datetime,
    end: datetime,
    max_seconds: int,
) -> datetime:
    remaining_ms = int((end - base).total_seconds() * 1_000)
    if remaining_ms < 1:
        raise ValueError(f"no timestamp available after {format_datetime(base)}")
    safe_remaining_ms = max(1, remaining_ms // 2)
    delta_ms = rng.randint(1, min(safe_remaining_ms, max_seconds * 1_000))
    return base + timedelta(milliseconds=delta_ms)


def weighted_order_timestamp(
    rng: random.Random,
    days: Sequence[date],
    day_weights: Sequence[float],
    latest: datetime,
) -> datetime:
    hour_weights = (
        0.3, 0.2, 0.15, 0.12, 0.12, 0.2,
        0.5, 0.9, 1.3, 1.5, 1.4, 1.8,
        2.0, 1.7, 1.4, 1.3, 1.5, 2.0,
        2.5, 2.8, 2.6, 2.0, 1.2, 0.7,
    )
    while True:
        chosen_day = rng.choices(days, weights=day_weights, k=1)[0]
        hour = rng.choices(range(24), weights=hour_weights, k=1)[0]
        result = datetime.combine(
            chosen_day,
            datetime_time(
                hour=hour,
                minute=rng.randrange(60),
                second=rng.randrange(60),
                microsecond=rng.randrange(1_000) * 1_000,
            ),
        )
        if result <= latest:
            return result


def generate_catalog(
    rng: random.Random,
    config: dict[str, int],
    range_start: datetime,
) -> tuple[list[Row], list[Row], list[Row]]:
    categories: list[Row] = []
    for index in range(config["root_categories"]):
        category_id = index + 1
        categories.append(
            {
                "category_id": category_id,
                "parent_category_id": None,
                "category_code": f"CAT-R{category_id:02d}",
                "category_name": f"Synthetic Department {category_id:02d}",
                "category_level": 1,
                "sort_order": category_id,
                "category_status": 1,
                "created_at": range_start,
                "updated_at": range_start,
            }
        )

    leaf_ids: list[int] = []
    for index in range(config["leaf_categories"]):
        category_id = config["root_categories"] + index + 1
        parent_id = index % config["root_categories"] + 1
        leaf_ids.append(category_id)
        categories.append(
            {
                "category_id": category_id,
                "parent_category_id": parent_id,
                "category_code": f"CAT-L{index + 1:02d}",
                "category_name": f"Synthetic Category {index + 1:02d}",
                "category_level": 2,
                "sort_order": index // config["root_categories"] + 1,
                "category_status": 1,
                "created_at": range_start,
                "updated_at": range_start,
            }
        )

    category_weights = [4.5, 3.5, 2.8, 2.3, 1.9, 1.6, 1.4, 1.25] + [1.0] * 8
    spus: list[Row] = []
    for index in range(config["spus"]):
        spu_id = index + 1
        category_id = rng.choices(leaf_ids, weights=category_weights, k=1)[0]
        brand = BRANDS[index % len(BRANDS)]
        noun = PRODUCT_NOUNS[(index * 5 + category_id) % len(PRODUCT_NOUNS)]
        spus.append(
            {
                "spu_id": spu_id,
                "category_id": category_id,
                "spu_code": f"SPU{spu_id:06d}",
                "spu_name": f"{brand} Synthetic {noun} {spu_id:03d}",
                "brand_name": brand,
                "spu_status": 1,
                "created_at": range_start,
                "updated_at": range_start,
            }
        )

    sku_counts = [3] * (config["skus"] - 2 * config["spus"]) + [2] * (
        3 * config["spus"] - config["skus"]
    )
    rng.shuffle(sku_counts)
    skus: list[Row] = []
    sku_id = 1
    price_points = (1999, 2999, 3999, 5999, 8999, 12999, 19999, 29999, 49999, 79999)
    for spu, sku_count in zip(spus, sku_counts):
        for variant in range(sku_count):
            color = COLORS[(spu["spu_id"] + variant * 2) % len(COLORS)]
            size = SIZES[(spu["spu_id"] * 3 + variant) % len(SIZES)]
            price_cents = price_points[(spu["spu_id"] + variant * 3) % len(price_points)]
            price_cents += (spu["category_id"] % 5) * 500
            skus.append(
                {
                    "sku_id": sku_id,
                    "spu_id": spu["spu_id"],
                    "category_id": spu["category_id"],
                    "sku_code": f"SKU{sku_id:06d}",
                    "sku_name": f"{spu['spu_name']} {color} {size}",
                    "specification_json": json.dumps(
                        {"color": color, "size": size},
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    "sale_price_cents": price_cents,
                    "sku_status": 1,
                    "created_at": range_start,
                    "updated_at": range_start,
                }
            )
            sku_id += 1
    return categories, spus, skus


def generate_users(
    rng: random.Random,
    count: int,
    range_start: datetime,
    range_end: datetime,
) -> list[Row]:
    total_ms = int((range_end - range_start).total_seconds() * 1_000)
    creation_window_ms = min(total_ms, 14 * 24 * 60 * 60 * 1_000)
    users: list[Row] = []
    for index in range(count):
        user_id = index + 1
        if index < 50:
            created_offset_ms = rng.randrange(min(creation_window_ms, 60 * 60 * 1_000) + 1)
        else:
            created_offset_ms = rng.randrange(creation_window_ms + 1)
        if index == 0:
            created_offset_ms = 0
        created_at = range_start + timedelta(milliseconds=created_offset_ms)
        users.append(
            {
                "user_id": user_id,
                "user_no": f"USER{user_id:08d}",
                "user_name": f"Synthetic User {user_id:06d}",
                "mobile": f"0000000{user_id:06d}",
                "email": f"user{user_id:06d}@example.test",
                "user_status": 1,
                "created_at": created_at,
                "updated_at": created_at,
                "activity_weight": (8.0 if index < 50 else 1.0) / ((index + 5) ** 0.28),
            }
        )
    return users


def choose_unique_skus(
    rng: random.Random,
    skus: Sequence[Row],
    weights: Sequence[float],
    count: int,
) -> list[Row]:
    chosen: list[Row] = []
    chosen_ids: set[int] = set()
    while len(chosen) < count:
        sku = rng.choices(skus, weights=weights, k=1)[0]
        if sku["sku_id"] not in chosen_ids:
            chosen.append(sku)
            chosen_ids.add(sku["sku_id"])
    return chosen


def payment_pattern(rng: random.Random, order_status: int, order_index: int) -> list[int]:
    forced = {
        0: [PAYMENT_SUCCEEDED],
        1: [PAYMENT_FAILED, PAYMENT_SUCCEEDED],
        2: [PAYMENT_FAILED, PAYMENT_FAILED],
        3: [PAYMENT_PENDING],
        4: [PAYMENT_CLOSED],
    }
    if order_index in forced:
        return forced[order_index]
    if order_status in (ORDER_PAID, ORDER_COMPLETED):
        roll = rng.random()
        if roll < 0.66:
            return [PAYMENT_SUCCEEDED]
        if roll < 0.92:
            return [PAYMENT_FAILED, PAYMENT_SUCCEEDED]
        return [PAYMENT_FAILED, PAYMENT_FAILED, PAYMENT_SUCCEEDED]
    if order_status == ORDER_PENDING:
        roll = rng.random()
        if roll < 0.55:
            return [PAYMENT_PENDING]
        if roll < 0.78:
            return [PAYMENT_FAILED, PAYMENT_PENDING]
        if roll < 0.93:
            return [PAYMENT_FAILED, PAYMENT_FAILED]
        return []
    roll = rng.random()
    if roll < 0.50:
        return [PAYMENT_CLOSED]
    if roll < 0.82:
        return [PAYMENT_FAILED, PAYMENT_CLOSED]
    if roll < 0.94:
        return [PAYMENT_FAILED]
    return []


def generate_orders_and_payments(
    rng: random.Random,
    config: dict[str, int],
    users: Sequence[Row],
    skus: Sequence[Row],
    range_start: datetime,
    range_end: datetime,
) -> tuple[list[Row], list[Row], list[Row]]:
    days = [
        range_start.date() + timedelta(days=offset)
        for offset in range((range_end.date() - range_start.date()).days + 1)
    ]
    day_weights = [1.25 if day.weekday() >= 5 else 1.0 for day in days]
    latest_order_time = range_end - timedelta(hours=2)

    users_by_creation = sorted(users, key=lambda user: (user["created_at"], user["user_id"]))
    user_creation_times = [user["created_at"] for user in users_by_creation]
    sku_weights = []
    category_rank = {category_id: rank for rank, category_id in enumerate(sorted({s["category_id"] for s in skus}))}
    for index, sku in enumerate(skus):
        hot_multiplier = 12.0 if index < 20 else 4.0 if index < 80 else 1.0
        category_multiplier = 3.5 / (1.0 + category_rank[sku["category_id"]] * 0.18)
        sku_weights.append(hot_multiplier * category_multiplier / ((index + 2) ** 0.42))

    orders: list[Row] = []
    details: list[Row] = []
    payments: list[Row] = []
    detail_id = 1
    payment_id = 1
    forced_order_statuses = (
        ORDER_COMPLETED,
        ORDER_PAID,
        ORDER_PENDING,
        ORDER_PENDING,
        ORDER_CANCELLED,
        ORDER_COMPLETED,
        ORDER_PAID,
        ORDER_CANCELLED,
    )

    for order_index in range(config["orders"]):
        order_id = order_index + 1
        ordered_at = weighted_order_timestamp(rng, days, day_weights, latest_order_time)
        eligible_count = bisect.bisect_right(user_creation_times, ordered_at)
        eligible_users = users_by_creation[:eligible_count]
        user = rng.choices(
            eligible_users,
            weights=[candidate["activity_weight"] for candidate in eligible_users],
            k=1,
        )[0]
        if order_index < len(forced_order_statuses):
            order_status = forced_order_statuses[order_index]
        else:
            order_status = rng.choices(
                (ORDER_PENDING, ORDER_PAID, ORDER_COMPLETED, ORDER_CANCELLED),
                weights=(0.11, 0.23, 0.57, 0.09),
                k=1,
            )[0]

        detail_count = rng.choices((1, 2, 3, 4, 5), weights=(15, 35, 30, 15, 5), k=1)[0]
        order_skus = choose_unique_skus(rng, skus, sku_weights, detail_count)
        order_amount_cents = 0
        order_details: list[Row] = []
        for detail_index, sku in enumerate(order_skus):
            quantity = 3 if order_index < 10 and detail_index == 0 else rng.choices(
                (1, 2, 3, 4), weights=(70, 20, 8, 2), k=1
            )[0]
            price_factor_basis_points = rng.randint(8_500, 10_500)
            unit_price_cents = max(1, sku["sale_price_cents"] * price_factor_basis_points // 10_000)
            line_amount_cents = unit_price_cents * quantity
            order_amount_cents += line_amount_cents
            detail = {
                "order_detail_id": detail_id,
                "order_id": order_id,
                "sku_id": sku["sku_id"],
                "sku_code_snapshot": sku["sku_code"],
                "sku_name_snapshot": sku["sku_name"],
                "unit_price_cents": unit_price_cents,
                "quantity": quantity,
                "line_amount_cents": line_amount_cents,
                "created_at": ordered_at,
            }
            details.append(detail)
            order_details.append(detail)
            detail_id += 1

        pattern = payment_pattern(rng, order_status, order_index)
        cursor = ordered_at
        success_payment_id: int | None = None
        success_paid_at: datetime | None = None
        for attempt_index, payment_status in enumerate(pattern, start=1):
            requested_at = random_after(rng, cursor, range_end, max_seconds=5 * 60)
            paid_at = None
            closed_at = None
            third_party_transaction_no = None
            if payment_status == PAYMENT_SUCCEEDED:
                paid_at = random_after(rng, requested_at, range_end, max_seconds=3 * 60)
                cursor = paid_at
                success_payment_id = payment_id
                success_paid_at = paid_at
                third_party_transaction_no = f"SYN-TXN-{payment_id:012d}"
            elif payment_status in (PAYMENT_FAILED, PAYMENT_CLOSED):
                closed_at = random_after(rng, requested_at, range_end, max_seconds=2 * 60)
                cursor = closed_at
            else:
                cursor = requested_at
            payments.append(
                {
                    "payment_id": payment_id,
                    "payment_no": f"PAY{payment_id:014d}",
                    "order_id": order_id,
                    "payment_attempt_no": attempt_index,
                    "payment_channel": rng.choices(
                        PAYMENT_CHANNELS, weights=PAYMENT_CHANNEL_WEIGHTS, k=1
                    )[0],
                    "payment_status": payment_status,
                    "payment_amount_cents": order_amount_cents,
                    "third_party_transaction_no": third_party_transaction_no,
                    "requested_at": requested_at,
                    "paid_at": paid_at,
                    "closed_at": closed_at,
                    "created_at": requested_at,
                    "updated_at": paid_at or closed_at or requested_at,
                }
            )
            payment_id += 1

        cancelled_at = None
        completed_at = None
        if order_status == ORDER_CANCELLED:
            cancelled_at = random_after(rng, cursor, range_end, max_seconds=30 * 60)
        elif order_status == ORDER_COMPLETED:
            if success_paid_at is None:
                raise AssertionError("completed order was generated without successful payment")
            completed_at = random_after(rng, success_paid_at, range_end, max_seconds=60 * 60)

        order_updated_at = completed_at or cancelled_at or success_paid_at or cursor
        orders.append(
            {
                "order_id": order_id,
                "order_no": f"ORD{order_id:014d}",
                "user_id": user["user_id"],
                "order_status": order_status,
                "order_amount_cents": order_amount_cents,
                "ordered_at": ordered_at,
                "cancelled_at": cancelled_at,
                "completed_at": completed_at,
                "created_at": ordered_at,
                "updated_at": order_updated_at,
                "success_payment_id": success_payment_id,
                "success_paid_at": success_paid_at,
                "details": order_details,
            }
        )
    return orders, details, payments


def generate_refunds(
    rng: random.Random,
    orders: Sequence[Row],
    payments: Sequence[Row],
    range_end: datetime,
) -> list[Row]:
    payment_by_id = {payment["payment_id"]: payment for payment in payments}
    contexts: list[tuple[Row, Row, Row]] = []
    for order in orders:
        success_payment_id = order["success_payment_id"]
        if success_payment_id is None:
            continue
        payment = payment_by_id[success_payment_id]
        for detail in order["details"]:
            contexts.append((order, detail, payment))
    contexts.sort(key=lambda context: (context[2]["paid_at"], context[1]["order_detail_id"]))

    if len(contexts) < 6:
        raise ValueError("not enough paid order details to create required refund scenarios")

    used_details: set[int] = set()

    def take_context(require_multiple_units: bool = False) -> tuple[Row, Row, Row]:
        for context in contexts:
            detail = context[1]
            if detail["order_detail_id"] in used_details:
                continue
            if require_multiple_units and detail["quantity"] < 3:
                continue
            used_details.add(detail["order_detail_id"])
            return context
        raise ValueError("not enough eligible order details for required refund scenarios")

    forced_specs: list[tuple[tuple[Row, Row, Row], int, int, int]] = []
    full_context = take_context()
    full_detail = full_context[1]
    forced_specs.append(
        (full_context, REFUND_SUCCEEDED, full_detail["quantity"], full_detail["line_amount_cents"])
    )

    partial_context = take_context()
    partial_detail = partial_context[1]
    forced_specs.append(
        (
            partial_context,
            REFUND_SUCCEEDED,
            1,
            max(1, partial_detail["unit_price_cents"] // 2),
        )
    )

    multi_context = take_context(require_multiple_units=True)
    multi_detail = multi_context[1]
    forced_specs.extend(
        [
            (multi_context, REFUND_SUCCEEDED, 1, multi_detail["unit_price_cents"]),
            (multi_context, REFUND_SUCCEEDED, 1, multi_detail["unit_price_cents"]),
        ]
    )

    for status in (REFUND_PENDING, REFUND_FAILED, REFUND_CANCELLED):
        context = take_context()
        detail = context[1]
        forced_specs.append((context, status, 1, detail["unit_price_cents"]))

    reserved_quantity: defaultdict[int, int] = defaultdict(int)
    reserved_amount: defaultdict[int, int] = defaultdict(int)
    detail_last_requested_at: dict[int, datetime] = {}
    refunds: list[Row] = []

    def append_refund(context: tuple[Row, Row, Row], status: int, quantity: int, amount: int) -> None:
        order, detail, payment = context
        detail_id = detail["order_detail_id"]
        base = max(payment["paid_at"], detail_last_requested_at.get(detail_id, payment["paid_at"]))
        requested_at = random_after(rng, base, range_end, max_seconds=14 * 24 * 60 * 60)
        refunded_at = None
        closed_at = None
        third_party_refund_no = None
        if status == REFUND_SUCCEEDED:
            refunded_at = random_after(rng, requested_at, range_end, max_seconds=2 * 24 * 60 * 60)
            third_party_refund_no = f"SYN-REF-{len(refunds) + 1:012d}"
        elif status in (REFUND_FAILED, REFUND_CANCELLED):
            closed_at = random_after(rng, requested_at, range_end, max_seconds=24 * 60 * 60)
        if status in RESERVED_REFUND_STATUSES:
            reserved_quantity[detail_id] += quantity
            reserved_amount[detail_id] += amount
        detail_last_requested_at[detail_id] = max(
            requested_at, refunded_at or requested_at, closed_at or requested_at
        )
        refund_id = len(refunds) + 1
        refunds.append(
            {
                "refund_id": refund_id,
                "refund_no": f"REF{refund_id:014d}",
                "order_id": order["order_id"],
                "order_detail_id": detail_id,
                "payment_id": payment["payment_id"],
                "refund_status": status,
                "refund_quantity": quantity,
                "refund_amount_cents": amount,
                "refund_reason": rng.choice(REFUND_REASONS),
                "third_party_refund_no": third_party_refund_no,
                "requested_at": requested_at,
                "refunded_at": refunded_at,
                "closed_at": closed_at,
                "created_at": requested_at,
                "updated_at": refunded_at or closed_at or requested_at,
            }
        )

    for context, status, quantity, amount in forced_specs:
        append_refund(context, status, quantity, amount)

    forced_context_details = {context[1]["order_detail_id"] for context, _, _, _ in forced_specs}
    for context in contexts:
        _, detail, _ = context
        detail_id = detail["order_detail_id"]
        if detail_id in forced_context_details or rng.random() >= 0.035:
            continue
        status = rng.choices(
            (REFUND_PENDING, REFUND_SUCCEEDED, REFUND_FAILED, REFUND_CANCELLED),
            weights=(12, 62, 16, 10),
            k=1,
        )[0]
        if status in RESERVED_REFUND_STATUSES:
            remaining_quantity = detail["quantity"] - reserved_quantity[detail_id]
            remaining_amount = detail["line_amount_cents"] - reserved_amount[detail_id]
            if remaining_quantity <= 0 or remaining_amount <= 0:
                continue
            quantity = rng.randint(1, remaining_quantity)
            amount = min(remaining_amount, detail["unit_price_cents"] * quantity)
        else:
            quantity = rng.randint(1, detail["quantity"])
            amount = detail["unit_price_cents"] * quantity
        append_refund(context, status, quantity, amount)
    return refunds


def verify_data(data: dict[str, list[Row]], range_start: datetime, range_end: datetime) -> None:
    users = data["users"]
    skus = data["skus"]
    orders = data["orders"]
    details = data["details"]
    payments = data["payments"]
    refunds = data["refunds"]

    user_by_id = {row["user_id"]: row for row in users}
    sku_by_id = {row["sku_id"]: row for row in skus}
    order_by_id = {row["order_id"]: row for row in orders}
    detail_by_id = {row["order_detail_id"]: row for row in details}
    payment_by_id = {row["payment_id"]: row for row in payments}

    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    for user in users:
        check(range_start <= user["created_at"] <= range_end, f"user {user['user_id']} created_at outside range")

    details_by_order: defaultdict[int, list[Row]] = defaultdict(list)
    for detail in details:
        details_by_order[detail["order_id"]].append(detail)
        check(detail["sku_id"] in sku_by_id, f"detail {detail['order_detail_id']} has unknown SKU")
        check(detail["quantity"] > 0, f"detail {detail['order_detail_id']} has invalid quantity")
        check(
            detail["line_amount_cents"] == detail["unit_price_cents"] * detail["quantity"],
            f"detail {detail['order_detail_id']} line amount mismatch",
        )

    payments_by_order: defaultdict[int, list[Row]] = defaultdict(list)
    for payment in payments:
        payments_by_order[payment["order_id"]].append(payment)
        order = order_by_id.get(payment["order_id"])
        check(order is not None, f"payment {payment['payment_id']} has unknown order")
        if order is None:
            continue
        check(
            payment["payment_amount_cents"] == order["order_amount_cents"],
            f"payment {payment['payment_id']} amount differs from order",
        )
        check(order["ordered_at"] <= payment["requested_at"], f"payment {payment['payment_id']} predates order")
        check(
            range_start <= payment["requested_at"] <= range_end,
            f"payment {payment['payment_id']} requested_at outside range",
        )
        if payment["payment_status"] == PAYMENT_SUCCEEDED:
            check(payment["paid_at"] is not None, f"successful payment {payment['payment_id']} has no paid_at")
            check(payment["closed_at"] is None, f"successful payment {payment['payment_id']} has closed_at")
            if payment["paid_at"] is not None:
                check(payment["requested_at"] <= payment["paid_at"], f"payment {payment['payment_id']} time order invalid")
                check(payment["paid_at"] <= range_end, f"payment {payment['payment_id']} paid_at outside range")
        elif payment["payment_status"] == PAYMENT_PENDING:
            check(payment["paid_at"] is None and payment["closed_at"] is None, f"pending payment {payment['payment_id']} has terminal time")
        else:
            check(payment["paid_at"] is None, f"non-success payment {payment['payment_id']} has paid_at")
            check(payment["closed_at"] is not None, f"terminal payment {payment['payment_id']} has no closed_at")
            if payment["closed_at"] is not None:
                check(payment["requested_at"] <= payment["closed_at"] <= range_end, f"payment {payment['payment_id']} closed_at outside range")

    for order in orders:
        order_id = order["order_id"]
        check(order["user_id"] in user_by_id, f"order {order_id} has unknown user")
        if order["user_id"] in user_by_id:
            check(user_by_id[order["user_id"]]["created_at"] <= order["ordered_at"], f"order {order_id} predates user")
        check(range_start <= order["ordered_at"] <= range_end, f"order {order_id} outside range")
        order_details = details_by_order[order_id]
        check(bool(order_details), f"order {order_id} has no details")
        check(
            sum(row["line_amount_cents"] for row in order_details) == order["order_amount_cents"],
            f"order {order_id} amount differs from detail sum",
        )
        check(
            len({row["sku_id"] for row in order_details}) == len(order_details),
            f"order {order_id} contains duplicate SKU details",
        )
        order_payments = sorted(payments_by_order[order_id], key=lambda row: row["payment_attempt_no"])
        check(
            [row["payment_attempt_no"] for row in order_payments] == list(range(1, len(order_payments) + 1)),
            f"order {order_id} has non-contiguous payment attempts",
        )
        successes = [row for row in order_payments if row["payment_status"] == PAYMENT_SUCCEEDED]
        check(len(successes) <= 1, f"order {order_id} has multiple successful payments")
        if order["order_status"] in (ORDER_PAID, ORDER_COMPLETED):
            check(len(successes) == 1, f"paid/completed order {order_id} lacks successful payment")
        else:
            check(not successes, f"pending/cancelled order {order_id} has successful payment")
        if order["order_status"] == ORDER_COMPLETED:
            check(order["completed_at"] is not None, f"completed order {order_id} has no completed_at")
            if successes and order["completed_at"] is not None:
                check(successes[0]["paid_at"] <= order["completed_at"], f"order {order_id} completed before payment")
                check(order["completed_at"] <= range_end, f"order {order_id} completed_at outside range")
        else:
            check(order["completed_at"] is None, f"non-completed order {order_id} has completed_at")
        if order["order_status"] == ORDER_CANCELLED:
            check(order["cancelled_at"] is not None, f"cancelled order {order_id} has no cancelled_at")
            if order["cancelled_at"] is not None:
                check(order["ordered_at"] <= order["cancelled_at"] <= range_end, f"order {order_id} cancelled_at outside range")
        else:
            check(order["cancelled_at"] is None, f"non-cancelled order {order_id} has cancelled_at")

    reserved_quantity: defaultdict[int, int] = defaultdict(int)
    reserved_amount: defaultdict[int, int] = defaultdict(int)
    refunds_by_detail: defaultdict[int, list[Row]] = defaultdict(list)
    for refund in refunds:
        order = order_by_id.get(refund["order_id"])
        detail = detail_by_id.get(refund["order_detail_id"])
        payment = payment_by_id.get(refund["payment_id"])
        check(order is not None, f"refund {refund['refund_id']} has unknown order")
        check(detail is not None, f"refund {refund['refund_id']} has unknown detail")
        check(payment is not None, f"refund {refund['refund_id']} has unknown payment")
        if order is None or detail is None or payment is None:
            continue
        check(detail["order_id"] == order["order_id"], f"refund {refund['refund_id']} detail belongs to another order")
        check(payment["order_id"] == order["order_id"], f"refund {refund['refund_id']} payment belongs to another order")
        check(payment["payment_status"] == PAYMENT_SUCCEEDED, f"refund {refund['refund_id']} payment is not successful")
        check(payment["paid_at"] is not None, f"refund {refund['refund_id']} payment has no paid_at")
        if payment["paid_at"] is not None:
            check(payment["paid_at"] <= refund["requested_at"], f"refund {refund['refund_id']} predates payment")
        check(
            range_start <= refund["requested_at"] <= range_end,
            f"refund {refund['refund_id']} requested_at outside range",
        )
        if refund["refund_status"] == REFUND_SUCCEEDED:
            check(refund["refunded_at"] is not None, f"successful refund {refund['refund_id']} has no refunded_at")
            check(refund["closed_at"] is None, f"successful refund {refund['refund_id']} has closed_at")
            if refund["refunded_at"] is not None:
                check(refund["requested_at"] <= refund["refunded_at"], f"refund {refund['refund_id']} time order invalid")
                check(refund["refunded_at"] <= range_end, f"refund {refund['refund_id']} refunded_at outside range")
        elif refund["refund_status"] == REFUND_PENDING:
            check(refund["refunded_at"] is None and refund["closed_at"] is None, f"pending refund {refund['refund_id']} has terminal time")
        else:
            check(refund["refunded_at"] is None, f"non-success refund {refund['refund_id']} has refunded_at")
            check(refund["closed_at"] is not None, f"terminal refund {refund['refund_id']} has no closed_at")
            if refund["closed_at"] is not None:
                check(refund["requested_at"] <= refund["closed_at"] <= range_end, f"refund {refund['refund_id']} closed_at outside range")
        if refund["refund_status"] in RESERVED_REFUND_STATUSES:
            reserved_quantity[detail["order_detail_id"]] += refund["refund_quantity"]
            reserved_amount[detail["order_detail_id"]] += refund["refund_amount_cents"]
        refunds_by_detail[detail["order_detail_id"]].append(refund)

    for detail_id, quantity in reserved_quantity.items():
        detail = detail_by_id[detail_id]
        check(quantity <= detail["quantity"], f"detail {detail_id} reserved refund quantity exceeded")
        check(reserved_amount[detail_id] <= detail["line_amount_cents"], f"detail {detail_id} reserved refund amount exceeded")

    order_statuses = {row["order_status"] for row in orders}
    payment_statuses = {row["payment_status"] for row in payments}
    refund_statuses = {row["refund_status"] for row in refunds}
    check(order_statuses == {10, 20, 30, 40}, "required order statuses are not all present")
    check(payment_statuses == {10, 20, 30, 40}, "required payment statuses are not all present")
    check(refund_statuses == {10, 20, 30, 40}, "required refund statuses are not all present")
    check({row["payment_channel"] for row in payments} == set(PAYMENT_CHANNELS), "required payment channels are not all present")
    check(
        any(len(rows) >= 2 and rows[0]["payment_status"] == PAYMENT_FAILED and rows[1]["payment_status"] == PAYMENT_SUCCEEDED for rows in payments_by_order.values()),
        "failed-then-successful payment scenario is absent",
    )
    check(
        any(len(rows) >= 1 and rows[0]["payment_status"] == PAYMENT_SUCCEEDED for rows in payments_by_order.values()),
        "first-attempt successful payment scenario is absent",
    )
    check(
        any(sum(row["payment_status"] == PAYMENT_FAILED for row in rows) >= 2 for rows in payments_by_order.values()),
        "multiple-failed-payment scenario is absent",
    )
    check(
        any(row["refund_quantity"] == detail_by_id[row["order_detail_id"]]["quantity"] and row["refund_amount_cents"] == detail_by_id[row["order_detail_id"]]["line_amount_cents"] for row in refunds),
        "full refund scenario is absent",
    )
    check(
        any(row["refund_quantity"] < detail_by_id[row["order_detail_id"]]["quantity"] or row["refund_amount_cents"] < detail_by_id[row["order_detail_id"]]["line_amount_cents"] for row in refunds),
        "partial refund scenario is absent",
    )
    check(
        any(
            len(rows) >= 2
            and all(
                row["refund_quantity"] < detail_by_id[detail_id]["quantity"]
                or row["refund_amount_cents"] < detail_by_id[detail_id]["line_amount_cents"]
                for row in rows
            )
            for detail_id, rows in refunds_by_detail.items()
        ),
        "multiple partial refunds on one detail are absent",
    )
    check(len(refunds_by_detail) < len(details), "no-refund scenario is absent")

    if errors:
        preview = "\n".join(f"- {message}" for message in errors[:20])
        suffix = f"\n... and {len(errors) - 20} more" if len(errors) > 20 else ""
        raise ValueError(f"generated data failed verification:\n{preview}{suffix}")


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if isinstance(value, datetime):
        value = format_datetime(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def write_insert_batches(
    output: TextIO,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    batch_size: int = 500,
) -> None:
    batch: list[Sequence[Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) == batch_size:
            write_insert(output, table, columns, batch)
            batch.clear()
    if batch:
        write_insert(output, table, columns, batch)


def write_insert(output: TextIO, table: str, columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    output.write(f"INSERT INTO `{table}` ({', '.join(f'`{column}`' for column in columns)}) VALUES\n")
    for index, row in enumerate(rows):
        ending = ";\n" if index == len(rows) - 1 else ",\n"
        output.write("(" + ", ".join(sql_literal(value) for value in row) + ")" + ending)
    output.write("\n")


def write_sql(path: Path, args: argparse.Namespace, data: dict[str, list[Row]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=".commerceai-data-",
            suffix=".sql.tmp",
            delete=False,
        ) as output:
            temp_path = Path(output.name)
            output.write("-- CommerceAI deterministic synthetic data\n")
            output.write(f"-- scale={args.scale} seed={args.seed} start_date={args.start_date} end_date={args.end_date}\n")
            output.write("-- Import after source/mysql/schema.sql into an empty database.\n\n")
            output.write("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci;\n")
            output.write("START TRANSACTION;\n\n")

            write_insert_batches(
                output,
                "user_info",
                ("user_id", "user_no", "user_name", "mobile", "email", "user_status", "created_at", "updated_at"),
                (
                    (row["user_id"], row["user_no"], row["user_name"], row["mobile"], row["email"], row["user_status"], row["created_at"], row["updated_at"])
                    for row in data["users"]
                ),
            )
            write_insert_batches(
                output,
                "category_info",
                ("category_id", "parent_category_id", "category_code", "category_name", "category_level", "sort_order", "category_status", "created_at", "updated_at"),
                (
                    (row["category_id"], row["parent_category_id"], row["category_code"], row["category_name"], row["category_level"], row["sort_order"], row["category_status"], row["created_at"], row["updated_at"])
                    for row in data["categories"]
                ),
            )
            write_insert_batches(
                output,
                "spu_info",
                ("spu_id", "category_id", "spu_code", "spu_name", "brand_name", "spu_status", "created_at", "updated_at"),
                (
                    (row["spu_id"], row["category_id"], row["spu_code"], row["spu_name"], row["brand_name"], row["spu_status"], row["created_at"], row["updated_at"])
                    for row in data["spus"]
                ),
            )
            write_insert_batches(
                output,
                "sku_info",
                ("sku_id", "spu_id", "sku_code", "sku_name", "specification_json", "sale_price", "sku_status", "created_at", "updated_at"),
                (
                    (row["sku_id"], row["spu_id"], row["sku_code"], row["sku_name"], row["specification_json"], money(row["sale_price_cents"]), row["sku_status"], row["created_at"], row["updated_at"])
                    for row in data["skus"]
                ),
            )
            write_insert_batches(
                output,
                "order_info",
                ("order_id", "order_no", "user_id", "order_status", "order_amount", "ordered_at", "cancelled_at", "completed_at", "created_at", "updated_at"),
                (
                    (row["order_id"], row["order_no"], row["user_id"], row["order_status"], money(row["order_amount_cents"]), row["ordered_at"], row["cancelled_at"], row["completed_at"], row["created_at"], row["updated_at"])
                    for row in data["orders"]
                ),
            )
            write_insert_batches(
                output,
                "order_detail",
                ("order_detail_id", "order_id", "sku_id", "sku_code_snapshot", "sku_name_snapshot", "unit_price", "quantity", "line_amount", "created_at"),
                (
                    (row["order_detail_id"], row["order_id"], row["sku_id"], row["sku_code_snapshot"], row["sku_name_snapshot"], money(row["unit_price_cents"]), row["quantity"], money(row["line_amount_cents"]), row["created_at"])
                    for row in data["details"]
                ),
            )
            write_insert_batches(
                output,
                "payment_info",
                ("payment_id", "payment_no", "order_id", "payment_attempt_no", "payment_channel", "payment_status", "payment_amount", "third_party_transaction_no", "requested_at", "paid_at", "closed_at", "created_at", "updated_at"),
                (
                    (row["payment_id"], row["payment_no"], row["order_id"], row["payment_attempt_no"], row["payment_channel"], row["payment_status"], money(row["payment_amount_cents"]), row["third_party_transaction_no"], row["requested_at"], row["paid_at"], row["closed_at"], row["created_at"], row["updated_at"])
                    for row in data["payments"]
                ),
            )
            write_insert_batches(
                output,
                "refund_info",
                ("refund_id", "refund_no", "order_id", "order_detail_id", "payment_id", "refund_status", "refund_quantity", "refund_amount", "refund_reason", "third_party_refund_no", "requested_at", "refunded_at", "closed_at", "created_at", "updated_at"),
                (
                    (row["refund_id"], row["refund_no"], row["order_id"], row["order_detail_id"], row["payment_id"], row["refund_status"], row["refund_quantity"], money(row["refund_amount_cents"]), row["refund_reason"], row["third_party_refund_no"], row["requested_at"], row["refunded_at"], row["closed_at"], row["created_at"], row["updated_at"])
                    for row in data["refunds"]
                ),
            )
            output.write("COMMIT;\n")
        os.replace(temp_path, path)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def generate(args: argparse.Namespace) -> dict[str, list[Row]]:
    rng = random.Random(args.seed)
    config = SCALE_CONFIG[args.scale]
    range_start = datetime.combine(args.start_date, datetime_time.min)
    range_end = datetime.combine(args.end_date, datetime_time.max).replace(microsecond=999_000)
    categories, spus, skus = generate_catalog(rng, config, range_start)
    users = generate_users(rng, config["users"], range_start, range_end)
    orders, details, payments = generate_orders_and_payments(
        rng, config, users, skus, range_start, range_end
    )
    refunds = generate_refunds(rng, orders, payments, range_end)
    data = {
        "users": users,
        "categories": categories,
        "spus": spus,
        "skus": skus,
        "orders": orders,
        "details": details,
        "payments": payments,
        "refunds": refunds,
    }
    verify_data(data, range_start, range_end)
    return data


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    try:
        data = generate(args)
        write_sql(args.output, args, data)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    elapsed = time.perf_counter() - started
    counts = {name: len(rows) for name, rows in data.items()}
    order_statuses = Counter(row["order_status"] for row in data["orders"])
    payment_statuses = Counter(row["payment_status"] for row in data["payments"])
    refund_statuses = Counter(row["refund_status"] for row in data["refunds"])
    print(f"generated: {args.output}")
    print("counts: " + " ".join(f"{name}={count}" for name, count in counts.items()))
    print(f"order_statuses: {dict(sorted(order_statuses.items()))}")
    print(f"payment_statuses: {dict(sorted(payment_statuses.items()))}")
    print(f"refund_statuses: {dict(sorted(refund_statuses.items()))}")
    print(f"verification: passed")
    print(f"sha256: {file_sha256(args.output)}")
    print(f"elapsed_seconds: {elapsed:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
