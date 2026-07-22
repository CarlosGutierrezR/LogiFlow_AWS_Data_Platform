"""Pruebas del generador sintético (contratos v1.0)."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pytest

from src.data_generator.config import (
    EVENT_TYPES,
    SERVICE_LEVELS,
    SHIPMENT_STATUSES,
    GeneratorConfig,
)
from src.data_generator.error_injector import inject_errors
from src.data_generator.generator import generate_all
from src.data_generator.main import run
from src.data_generator.writers import landing_path


def _cfg(tmp_path: Path, **overrides) -> GeneratorConfig:
    defaults = dict(
        ingest_date=date(2026, 7, 22),
        output_dir=tmp_path,
        num_orders=50,
        error_rate=0.0,
        seed=123,
    )
    defaults.update(overrides)
    return GeneratorConfig(**defaults)


class TestCleanGeneration:
    def test_counts_and_relations(self, tmp_path: Path) -> None:
        cfg = _cfg(tmp_path)
        data = generate_all(cfg)

        assert len(data["warehouses"]) == cfg.num_warehouses
        assert len(data["routes"]) == cfg.num_routes
        assert len(data["orders"]) == cfg.num_orders
        assert len(data["shipments"]) == cfg.num_orders  # 1:1 con orders

        warehouse_ids = {w["warehouse_id"] for w in data["warehouses"]}
        order_ids = {o["order_id"] for o in data["orders"]}
        shipment_ids = {s["shipment_id"] for s in data["shipments"]}

        assert all(r["origin_warehouse_id"] in warehouse_ids for r in data["routes"])
        assert all(o["origin_warehouse_id"] in warehouse_ids for o in data["orders"])
        assert all(s["order_id"] in order_ids for s in data["shipments"])
        assert all(
            e["shipment_id"] in shipment_ids for e in data["delivery_events"]
        )

    def test_primary_keys_unique_and_patterns(self, tmp_path: Path) -> None:
        data = generate_all(_cfg(tmp_path))
        orders = [o["order_id"] for o in data["orders"]]
        shipments = [s["shipment_id"] for s in data["shipments"]]
        events = [e["event_id"] for e in data["delivery_events"]]

        assert len(orders) == len(set(orders))
        assert len(shipments) == len(set(shipments))
        assert len(events) == len(set(events))
        assert all(re.fullmatch(r"ORD-\d{8}-\d{5}", o) for o in orders)
        assert all(re.fullmatch(r"SHP-\d{8}-\d{5}", s) for s in shipments)

    def test_enums_and_ranges(self, tmp_path: Path) -> None:
        data = generate_all(_cfg(tmp_path))
        assert all(o["service_level"] in SERVICE_LEVELS for o in data["orders"])
        assert all(s["status"] in SHIPMENT_STATUSES for s in data["shipments"])
        assert all(
            e["event_type"] in EVENT_TYPES for e in data["delivery_events"]
        )
        assert all(o["total_weight_kg"] > 0 for o in data["orders"])
        assert all(s["cost_eur"] > 0 for s in data["shipments"])

    def test_temporal_coherence(self, tmp_path: Path) -> None:
        data = generate_all(_cfg(tmp_path))
        for s in data["shipments"]:
            assert s["planned_delivery_ts"] > s["planned_departure_ts"]
            if s["actual_departure_ts"] and s["actual_delivery_ts"]:
                assert s["actual_delivery_ts"] > s["actual_departure_ts"]

    def test_reproducible_with_same_seed(self, tmp_path: Path) -> None:
        assert generate_all(_cfg(tmp_path)) == generate_all(_cfg(tmp_path))

    def test_different_seed_changes_output(self, tmp_path: Path) -> None:
        a = generate_all(_cfg(tmp_path, seed=1))
        b = generate_all(_cfg(tmp_path, seed=2))
        assert a != b


class TestErrorInjection:
    def test_zero_rate_injects_nothing(self, tmp_path: Path) -> None:
        clean = generate_all(_cfg(tmp_path))
        dirty, manifest = inject_errors(clean, error_rate=0.0, seed=123)
        assert manifest == []
        assert dirty == clean

    def test_manifest_matches_mutations(self, tmp_path: Path) -> None:
        clean = generate_all(_cfg(tmp_path))
        dirty, manifest = inject_errors(clean, error_rate=0.05, seed=123)

        assert len(manifest) > 0
        valid_codes = {"E01", "E02", "E03", "E04", "E05", "E06", "E07"}
        assert {m["error_code"] for m in manifest} <= valid_codes

        # E02 añade filas duplicadas: el total crece exactamente en los E02.
        e02_count = sum(1 for m in manifest if m["error_code"] == "E02")
        total_clean = sum(len(v) for v in clean.values())
        total_dirty = sum(len(v) for v in dirty.values())
        assert total_dirty == total_clean + e02_count

    def test_clean_data_not_mutated(self, tmp_path: Path) -> None:
        clean = generate_all(_cfg(tmp_path))
        snapshot = json.dumps(clean, sort_keys=True, default=str)
        inject_errors(clean, error_rate=0.10, seed=99)
        assert json.dumps(clean, sort_keys=True, default=str) == snapshot


class TestEndToEnd:
    def test_cli_writes_all_files(self, tmp_path: Path) -> None:
        exit_code = run(
            [
                "--date",
                "2026-07-22",
                "--output-dir",
                str(tmp_path),
                "--num-orders",
                "40",
                "--error-rate",
                "0.02",
            ]
        )
        assert exit_code == 0

        for entity in ("warehouses", "routes", "orders", "shipments"):
            assert landing_path(tmp_path, entity, date(2026, 7, 22)).exists()
        assert landing_path(tmp_path, "delivery_events", date(2026, 7, 22)).exists()

        manifest_path = tmp_path / "_manifests" / "errors_manifest_20260722.json"
        assert manifest_path.exists()
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert payload["injected_error_count"] == len(payload["errors"])
        assert payload["injected_error_count"] > 0

    def test_cli_rejects_bad_date(self, tmp_path: Path) -> None:
        assert run(["--date", "22-07-2026", "--output-dir", str(tmp_path)]) == 2


class TestConfigValidation:
    def test_invalid_error_rate(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            _cfg(tmp_path, error_rate=0.9)

    def test_invalid_num_orders(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            _cfg(tmp_path, num_orders=0)
