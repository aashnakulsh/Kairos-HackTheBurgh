"""Optional real-data tests use tiny invented inputs; no raw files, weights or network."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from importlib.util import find_spec
import unittest

MARKET_AVAILABLE = all(find_spec(name) for name in ("numpy", "pandas", "pyarrow", "bs4", "pypdf", "exchange_calendars"))
if MARKET_AVAILABLE:
    import numpy as np
    import pandas as pd
    from data.real_market import (MarketInputs, UnsupportedInput, audit_prices, parse_release,
                                  sessions, CUTOFF, DATES, digest)
    from training.chronos_adapter import ChronosAdapter, MODEL_VERSION, model_frames
    from training.baseline import EmpiricalBaseline, completed_windows


def fake_inputs():
    inputs = MarketInputs.__new__(MarketInputs)
    inputs.manifest = dict(cutoff=CUTOFF, base_date="2025-05-01", base_value=100.0,
                           dataset_version="test-only", assumptions=["Invented unit-test data"])
    inputs.schedule = sessions("2025-05-01", "2025-06-30")
    available = inputs.schedule[inputs.schedule.close < pd.Timestamp(CUTOFF)]
    inputs.prices = pd.DataFrame(dict(date=available.date,
        available_at=available.close.map(lambda d: d.isoformat()), level=np.arange(len(available)) + 100.0))
    inputs.releases = pd.DataFrame([
        dict(published_at="2025-05-13T12:30:00Z", reference_month="2025-04", cpi_percent=0.2),
        dict(published_at="2025-06-11T12:30:00Z", reference_month="2025-05", cpi_percent=0.1)])
    return inputs


class FakePipeline:
    def __init__(self, bad=None):
        self.calls = []
        self.bad = bad

    def predict_df(self, past, future_df, **kwargs):
        self.calls.append((past.copy(), future_df.copy(), kwargs))
        result = future_df[["item_id", "timestamp"]].copy()
        for q, v in [("0.1", 99.0), ("0.5", 100.0), ("0.9", 101.0)]:
            result[q] = v
        if self.bad == "nan":
            result.loc[0, "0.5"] = float("nan")
        elif self.bad == "crossed":
            result.loc[0, "0.9"] = 98.0
        elif self.bad == "short":
            result = result.iloc[:-1]
        return result


@unittest.skipUnless(MARKET_AVAILABLE, "optional: pip install -r requirements-market.txt")
class MarketTests(unittest.TestCase):
    def test_calendar_holidays_dst_early_close_and_june_dates(self):
        s = sessions("2025-01-01", "2025-12-31").set_index("date")
        self.assertEqual(len(s), 250)
        self.assertNotIn("2025-01-09", s.index)
        self.assertNotIn("2025-06-19", s.index)
        self.assertEqual(s.loc["2025-07-03", "close"].hour, 17)
        self.assertEqual(s.loc["2025-01-02", "open"].hour, 14)
        self.assertEqual(s.loc["2025-06-11", "open"].hour, 13)
        self.assertEqual(s.loc["2025-06-11":"2025-06-17"].index.tolist(), DATES)

    def bars(self):
        times = pd.to_datetime(["2025-07-03 09:30", "2025-07-03 12:59", "2025-07-03 13:00"])
        return pd.DataFrame(dict(datetime=times, Open=100., High=102., Low=99., Close=101., Volume=10, source="iex"))

    def test_gap_audit_quarantines_after_close_and_keeps_close_availability(self):
        daily, audit, details = audit_prices(self.bars(), sessions("2025-07-03", "2025-07-07"))
        self.assertEqual(audit["outside_session_rows"], 1)
        self.assertEqual(audit["missing_minutes"], 208)
        self.assertEqual(daily.available_at.iloc[0], "2025-07-03T17:00:00Z")
        self.assertEqual(details.expected_minutes.iloc[0], 210)

    def test_duplicate_policy_and_invalid_bars(self):
        bars = self.bars()
        _, audit, _ = audit_prices(pd.concat([bars, bars.iloc[:1]]), sessions("2025-07-03", "2025-07-07"))
        self.assertEqual(audit["exact_duplicates"], 1)
        conflict = bars.iloc[:1].copy(); conflict["Close"] = 100.5
        with self.assertRaisesRegex(UnsupportedInput, "Conflicting"):
            audit_prices(pd.concat([bars, conflict]), sessions("2025-07-03", "2025-07-07"))
        bars.loc[0, "High"] = 1
        with self.assertRaisesRegex(UnsupportedInput, "Invalid OHLC"):
            audit_prices(bars, sessions("2025-07-03", "2025-07-07"))

    def test_missing_close_not_substituted(self):
        with self.assertRaisesRegex(UnsupportedInput, "No valid"):
            audit_prices(self.bars().iloc[:1], sessions("2025-07-03", "2025-07-07"))

    def test_original_release_publication_units_and_negative_reading(self):
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "cpi_06112025.htm"
            p.write_text('<pre>Embargoed until 8:30 a.m. (ET) Wednesday, June 11, 2025 '
                'CONSUMER PRICE INDEX - MAY 2025 The Consumer Price Index for All Urban '
                'Consumers (CPI-U) fell 0.1 percent in May on a seasonally adjusted basis.</pre>')
            r = parse_release(p)
            self.assertEqual(r["published_at"], "2025-06-11T12:30:00Z")
            self.assertEqual(r["reference_month"], "2025-05")
            self.assertEqual(r["cpi_percent"], -0.1)
            self.assertEqual(r["sha256"], digest(p))
            p.write_text(p.read_text().replace("seasonally adjusted", "unadjusted"))
            with self.assertRaisesRegex(UnsupportedInput, "units"):
                parse_release(p)

    def test_future_actual_cpi_and_prices_cannot_enter_request(self):
        i = fake_inputs()
        a = i.request(0.4, MODEL_VERSION)
        i.releases.loc[1, "cpi_percent"] = 99.0
        i.prices = pd.concat([i.prices, pd.DataFrame([dict(date="2025-06-11", level=999999.,
                                                       available_at="2025-06-11T20:00:00Z")])])
        self.assertEqual(a, i.request(0.4, MODEL_VERSION))
        b = i.request(0.2, MODEL_VERSION)
        self.assertEqual(a.history, b.history)
        self.assertEqual(len(a.history), 20)
        self.assertEqual([r.date for r in a.future], DATES)
        self.assertEqual([r.release_indicator for r in a.future], [1, 0, 0, 0, 0])
        self.assertEqual({r.cpi_percent for r in a.history}, {0.2})
        self.assertEqual({r.cpi_percent for r in a.future}, {0.4})
        past, future = model_frames(a)
        self.assertNotIn("target", future)
        self.assertTrue((pd.concat([past.timestamp, future.timestamp]).diff().dropna() == pd.Timedelta(days=1)).all())

    def test_missing_history_and_out_of_range_are_explicit(self):
        i = fake_inputs()
        with self.assertRaisesRegex(UnsupportedInput, "range"):
            i.request(99., MODEL_VERSION)
        i.prices = i.prices[i.prices.date != "2025-06-02"]
        with self.assertRaisesRegex(UnsupportedInput, "Missing close"):
            i.request(0.4, MODEL_VERSION)

    def test_publication_after_close_does_not_enter_that_sessions_history(self):
        i = fake_inputs()
        i.releases = pd.concat([i.releases, pd.DataFrame([dict(published_at="2025-06-02T20:01:00Z",
                reference_month="2025-04", cpi_percent=.7)])]).sort_values("published_at")
        history = {r.date: r for r in i.request(.4, MODEL_VERSION).history}
        self.assertEqual(history["2025-06-02"].cpi_percent, .2)
        self.assertEqual(history["2025-06-03"].cpi_percent, .7)
        self.assertEqual(history["2025-06-03"].release_indicator, 1)
        self.assertEqual(history["2025-06-04"].release_indicator, 0)

    def test_processed_hash_validation_and_separate_reveal_reader(self):
        import json
        from data.reveal import read_reveal
        i = fake_inputs()
        with TemporaryDirectory() as tmp:
            root = Path(tmp); directory = root / "processed/test-only"; directory.mkdir(parents=True)
            reveal = root / "reveal/test-only"; reveal.mkdir(parents=True)
            frames = {"spy_daily.parquet": i.prices, "cpi_releases.parquet": i.releases,
                      "sessions.parquet": i.schedule}
            for name, frame in frames.items():
                frame.to_parquet(directory / name, index=False)
            i.prices.to_parquet(reveal / "spy_actuals.parquet", index=False)
            manifest = dict(i.manifest, files={name: digest(directory / name) for name in frames},
                            reveal_sha256=digest(reveal / "spy_actuals.parquet"))
            (directory / "manifest.json").write_text(json.dumps(manifest))
            loaded = MarketInputs(directory)
            request = loaded.request(.4, MODEL_VERSION)
            actuals = read_reveal(root, "test-only", ["2025-06-10"])
            self.assertEqual(actuals[0]["date"], "2025-06-10")
            self.assertEqual(request, loaded.request(.4, MODEL_VERSION))
            with self.assertRaisesRegex(UnsupportedInput, "missing"):
                read_reveal(root, "test-only", DATES)
            (reveal / "spy_actuals.parquet").write_bytes(b"corrupt")
            with self.assertRaisesRegex(UnsupportedInput, "hash"):
                read_reveal(root, "test-only", ["2025-06-10"])
            (directory / "spy_daily.parquet").write_bytes(b"corrupt")
            with self.assertRaisesRegex(UnsupportedInput, "hash"):
                MarketInputs(directory)

    def test_chronos_boundary_maps_sessions_and_reuses_pipeline(self):
        i = fake_inputs(); p = FakePipeline(); a = ChronosAdapter(i, pipeline=p)
        for cpi in (0.4, 0.2):
            r = a.forecast_segment(i.request(cpi, a.model_version))
            self.assertEqual(r.status, "supported", r.reason)
            self.assertEqual([p.date for p in r.points], DATES)
            self.assertTrue(all(p.q10 <= p.value <= p.q90 for p in r.points))
        self.assertEqual(len(p.calls), 2)
        self.assertEqual(p.calls[0][1].cpi_percent.tolist(), [0.4]*5)
        self.assertEqual(p.calls[1][1].cpi_percent.tolist(), [0.2]*5)

    def test_bad_model_output_and_wrong_snapshot_rejected(self):
        i = fake_inputs()
        for bad in ("nan", "crossed", "short"):
            with self.subTest(bad=bad):
                result = ChronosAdapter(i, FakePipeline(bad)).forecast_segment(i.request(.4, MODEL_VERSION))
                self.assertEqual(result.status, "unsupported")
                self.assertFalse(result.points)
        p = FakePipeline(); a = ChronosAdapter(i, p)
        for field, value in [("dataset_version", "wrong"), ("model_version", "wrong"), ("target_id", "QQQ")]:
            request = i.request(.4, MODEL_VERSION); setattr(request, field, value)
            self.assertEqual(a.forecast_segment(request).status, "unsupported")
        self.assertFalse(p.calls)

    def test_real_baselines_fail_honestly_with_small_sample(self):
        i = fake_inputs()
        for mode, count in [("reference", 1), ("analogue", 0)]:
            b = EmpiricalBaseline(i, mode)
            r = b.forecast_segment(i.request(.4, b.model_version))
            self.assertEqual((r.status, r.support_count), ("unsupported", count))

    def test_baseline_complete_cutoff_windows_and_eight_release_support(self):
        i = fake_inputs()
        schedule = sessions("2024-05-01", "2025-06-30")
        prices = pd.DataFrame(dict(date=schedule.date, level=np.arange(len(schedule)) * .1 + 100.,
            available_at=schedule.close.map(lambda d: d.isoformat())))
        dates = schedule.iloc[list(range(10, 191, 20))].open
        releases = pd.DataFrame(dict(published_at=dates.map(lambda t: (t-pd.Timedelta(hours=1)).isoformat()),
                                    reference_month=pd.period_range("2024-04", periods=len(dates), freq="M").astype(str),
                                    cpi_percent=.2))
        windows = completed_windows(prices, releases, schedule, CUTOFF)
        self.assertEqual(len(windows), 10)
        # A partially observed first window must not become a completed example.
        self.assertEqual(len(completed_windows(prices, releases, schedule, schedule.close.iloc[12])), 0)
        # Keep request validation bound to the fixture while exercising empirical samples.
        historical = SimpleNamespace(prices=prices, releases=releases, schedule=schedule, request=i.request)
        for mode, count in [("reference", 10), ("analogue", 9)]:
            b = EmpiricalBaseline(historical, mode)
            result = b.forecast_segment(i.request(.2, b.model_version))
            self.assertEqual(result.status, "supported", result.reason)
            self.assertEqual(result.support_count, count)
            self.assertTrue(all(p.q10 <= p.value <= p.q90 for p in result.points))
            self.assertIn("Eligible release dates:", result.assumptions[-1])
        releases.iloc[1, releases.columns.get_loc("reference_month")] = "2023-01"
        windows = completed_windows(prices, releases, schedule, CUTOFF)
        self.assertIsNone(windows[1]["delta"])


if __name__ == "__main__":
    unittest.main()
