"""Local, versioned SPY research inputs. No network, imputation, or model calls.

Price availability is a bar-end proxy, NOT proof of historical vendor delivery.
The downloaded, split-adjusted file is a current vintage, not point-in-time prices.
"""
from datetime import datetime
from hashlib import sha256
from importlib.metadata import version
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import exchange_calendars as xc
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pypdf import PdfReader

from api.contracts import ForecastRequest, FutureRow, HistoryRow
from api.cpi_domain import MIN_CPI, MAX_CPI, RELEASE_DATES

CUTOFF = "2025-06-11T12:29:59Z"
DATES = ["2025-06-11", "2025-06-12", "2025-06-13", "2025-06-16", "2025-06-17"]
POLICY = "iex-last-minute-close-cpi-publication-v1"
MONTHS = {name: i for i, name in enumerate(
    "January February March April May June July August September October November December".split(), 1)}
WARNINGS = [
    "Local academic research only; public demo/display and redistribution are not approved by this manifest.",
    "IEX-only last-minute price proxy, not the consolidated official close or total return.",
    "Current split-adjusted price vintage; historical bar-end availability is assumed, not verified vendor latency.",
    "Only 20 sessions have known CPI before this fork; no CPI history was backfilled.",
]


class UnsupportedInput(ValueError):
    """An explicit coverage or validation failure, never a synthetic fallback."""


def digest(path):
    with Path(path).open("rb") as stream:
        h = sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def instant(value):
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise UnsupportedInput("Timezone is required")
    return ts.tz_convert("UTC").isoformat().replace("+00:00", "Z")


def sessions(start, end):
    calendar = xc.get_calendar("XNYS", start=start, end=end)
    s = calendar.schedule.loc[start:end, ["open", "close"]].copy()
    s.insert(0, "date", s.index.strftime("%Y-%m-%d"))
    return s.reset_index(drop=True)


def validate_2025_calendar(schedule):
    """Cross-check software schedule against the visually reviewed supplied NYSE PDF."""
    year = schedule[schedule.date.str.startswith("2025-")]
    closed = sorted(set(pd.bdate_range("2025-01-01", "2025-12-31").strftime("%Y-%m-%d")) - set(year.date))
    expected = ["2025-01-01", "2025-01-09", "2025-01-20", "2025-02-17", "2025-04-18",
                "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25"]
    early = year[(year.close - year.open) == pd.Timedelta(hours=3, minutes=30)].date.tolist()
    if closed != expected or early != ["2025-07-03", "2025-11-28", "2025-12-24"]:
        raise UnsupportedInput("Software calendar disagrees with the reviewed 2025 NYSE dates")
    return dict(sessions=len(year), closed_weekdays=closed, early_closes=early,
                source="Supplied NYSE 2025 PDF, visually reviewed; exchange-calendars 4.13.2 XNYS")


def parse_release(path):
    """Read original release narrative, never revised historical CPI tables."""
    path = Path(path)
    if path.suffix == ".txt":
        text = " ".join(re.sub(r"(?m)^L\d+: ?", "", path.read_text()).split())
    else:
        soup = BeautifulSoup(path.read_bytes(), "html.parser")
        pre = soup.find("pre")
        if pre is None:
            raise UnsupportedInput(f"No original release narrative in {path.name}")
        text = " ".join(pre.get_text(" ").split())
    publication = re.search(r"8:30 a\.m\. \(ET\).*?([A-Z][a-z]+) (\d{1,2}), (\d{4})", text)
    period = re.search(r"CONSUMER PRICE INDEX [-–] ([A-Z]+) (\d{4})", text)
    reading = re.search(r"Consumer Price Index for All Urban Consumers \(CPI-U\) "
                        r"(increased|rose|decreased|declined|fell) (\d+(?:\.\d+)?) percent", text)
    if reading is None:
        # Original releases also express a zero monthly change without a number.
        text = re.sub(r"(Consumer Price Index for All Urban Consumers \(CPI-U\)) (?:was |remained )?unchanged",
                      r"\1 increased 0.0 percent", text)
        reading = re.search(r"Consumer Price Index for All Urban Consumers \(CPI-U\) "
                            r"(increased|rose|decreased|declined|fell) (\d+(?:\.\d+)?) percent", text)
    if not publication or not period or not reading:
        raise UnsupportedInput(f"Unrecognized CPI narrative in {path.name}; manual review required")
    month, day, year = publication.groups()
    dt = datetime(int(year), MONTHS[month], int(day), 8, 30, tzinfo=ZoneInfo("America/New_York"))
    expected_name = f"cpi_{dt:%m%d%Y}.htm"
    if path.stem != Path(expected_name).stem:
        raise UnsupportedInput("CPI filename and publication date disagree")
    # Verify the extracted value describes the seasonally adjusted monthly headline.
    if "seasonally adjusted basis" not in text[reading.end():reading.end() + 160]:
        raise UnsupportedInput("CPI units/adjustment could not be verified")
    value = float(reading[2]) * (-1 if reading[1] in {"decreased", "declined", "fell"} else 1)
    return dict(published_at=instant(dt), reference_month=f"{period[2]}-{MONTHS[period[1].title()]:02}",
                cpi_percent=value, source_url=f"https://www.bls.gov/news.release/archives/{expected_name}",
                sha256=digest(path), locator=("Official archive text retrieved through web tool; original narrative first paragraph"
                    if path.suffix == ".txt" else "original preformatted narrative, first paragraph"))


def audit_prices(frame, schedule):
    required = {"datetime", "Open", "High", "Low", "Close", "Volume", "source"}
    if set(frame.columns) != required or frame.empty:
        raise UnsupportedInput("Unexpected or empty SPY schema")
    x = frame.copy()
    if x.isna().any().any():
        raise UnsupportedInput("Null raw values require review")
    exact_duplicates = int(x.duplicated().sum())
    x = x.drop_duplicates()
    if x.datetime.duplicated().any():
        raise UnsupportedInput("Conflicting duplicate timestamps")
    if x.datetime.dt.tz is not None:
        raise UnsupportedInput("Expected naive provider timestamps documented as America/New_York")
    prices = x[["Open", "High", "Low", "Close"]]
    if (not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any()
        or (x.High < prices.max(axis=1)).any() or (x.Low > prices.min(axis=1)).any()
        or not np.isfinite(x.Volume).all() or (x.Volume < 0).any() or (x.Volume % 1 != 0).any()
        or set(x.source) != {"iex"}):
        raise UnsupportedInput("Invalid OHLC/volume or unsupported source")
    ts = x.datetime.dt.tz_localize("America/New_York", ambiguous="raise", nonexistent="raise")
    if not (ts == ts.dt.floor("min")).all():
        raise UnsupportedInput("Bars must be aligned to minute starts")
    monotonic = bool(x.datetime.is_monotonic_increasing)
    x["timestamp"] = ts.dt.tz_convert("UTC")
    x["date"] = ts.dt.strftime("%Y-%m-%d")
    x = x.sort_values("timestamp")
    merged = x.merge(schedule, on="date", how="left", validate="many_to_one")
    eligible = (merged.timestamp >= merged.open) & (merged.timestamp < merged.close)
    outside = int((~eligible).sum())
    # Outside-session records are quarantined and counted, never used as closes.
    groups = {d: g for d, g in merged[eligible].groupby("date")}
    details, daily = [], []
    first_date, last_date = x.date.min(), x.date.max()
    for row in schedule.itertuples(index=False):
        if not first_date <= row.date <= last_date:
            continue
        g = groups.get(row.date)
        expected = int((row.close - row.open).total_seconds() / 60)
        count = 0 if g is None else len(g)
        has_close = g is not None and g.timestamp.iloc[-1] == row.close - pd.Timedelta(minutes=1)
        missing = pd.date_range(row.open, row.close, freq="min", inclusive="left").difference(
            pd.DatetimeIndex([]) if g is None else pd.DatetimeIndex(g.timestamp))
        details.append(dict(date=row.date, expected_minutes=expected, recorded_minutes=count,
                            missing_minutes=expected - count, valid_close=bool(has_close),
                            missing_minute_starts=[instant(t) for t in missing]))
        if has_close:
            daily.append(dict(date=row.date, close_usd=float(g.Close.iloc[-1]),
                              available_at=instant(row.close), missing_minutes=expected-count))
    audit = dict(rows=len(frame), columns={c: str(frame[c].dtype) for c in frame},
                 first_timestamp=str(x.datetime.min()), last_timestamp=str(x.datetime.max()),
                 timezone="America/New_York", sorted=monotonic, exact_duplicates=exact_duplicates,
                 conflicting_duplicates=0, nulls=0, invalid_ohlc=0, outside_session_rows=outside,
                 outside_session_timestamps=[instant(t) for t in merged.loc[~eligible, "timestamp"]],
                 zero_volume_rows=int((x.Volume == 0).sum()), sessions=len(details),
                 missing_minutes=sum(d["missing_minutes"] for d in details),
                 missing_sessions=[d["date"] for d in details if not d["recorded_minutes"]],
                 missing_close_dates=[d["date"] for d in details if not d["valid_close"]],
                 sessions_with_gaps=sum(d["missing_minutes"] > 0 for d in details))
    if not daily:
        raise UnsupportedInput("No valid session close proxies")
    return pd.DataFrame(daily), audit, pd.DataFrame(details)


def build(root, cpi_directory=None):
    """Build the bounded June example. Every output is under the configured local root."""
    root = Path(root)
    raw = root / "raw"
    spy = raw / "hf/SPY_raw_1min.parquet"
    pdf = raw / "nyse/ICE_NYSE_2025_Yearly_Trading_Calendar.pdf"
    if "2025" not in PdfReader(pdf).pages[0].extract_text():
        raise UnsupportedInput("Expected the 2025 NYSE calendar")
    release_paths = sorted((raw / "bls").glob("cpi_*.htm"))
    if cpi_directory:
        extra = {p.stem: p for p in Path(cpi_directory).glob("cpi_*") if p.suffix in {".htm", ".txt"}}
        extra.update({p.stem: p for p in release_paths})
        release_paths = sorted(extra.values())
    releases = pd.DataFrame([parse_release(p) for p in release_paths]).sort_values("published_at")
    expected_periods = ["2025-04", "2025-05", "2025-06", "2025-07"]
    current = releases[releases.reference_month.isin(expected_periods)]
    if (current.reference_month.tolist() != expected_periods
        or current.published_at.tolist() != ["2025-05-13T12:30:00Z", "2025-06-11T12:30:00Z",
                                              "2025-07-15T12:30:00Z", "2025-08-12T12:30:00Z"]):
        raise UnsupportedInput("This snapshot requires the four original April–July 2025 CPI vintages")
    if releases.reference_month.tolist() != pd.period_range(releases.reference_month.iloc[0], releases.reference_month.iloc[-1], freq="M").astype(str).tolist():
        raise UnsupportedInput("CPI reference months must be consecutive and unique; missing vintages must be obtained")
    frame = pd.read_parquet(spy)
    schedule = sessions(f"{frame.datetime.min().year}-01-01", f"{frame.datetime.max().year}-12-31")
    calendar_check = validate_2025_calendar(schedule)
    daily, audit, gaps = audit_prices(frame, schedule)
    base = daily.iloc[0]
    daily["level"] = 100.0 * daily.close_usd / base.close_usd
    history = daily[pd.to_datetime(daily.available_at) <= pd.Timestamp(CUTOFF)].copy()
    sources = [dict(path=str(p.relative_to(root)), sha256=digest(p), bytes=p.stat().st_size)
               for p in [spy, *release_paths, pdf]]
    packages = {p: version(p) for p in ["pandas", "numpy", "pyarrow", "exchange-calendars", "beautifulsoup4", "pypdf", "tzdata"]}
    identity = dict(policy=POLICY + ("-expanded-context252-v2" if cpi_directory else ""), sources=sources, packages=packages, cutoff=CUTOFF)
    dataset_version = "spy-" + sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    directory = root / "processed" / dataset_version
    directory.mkdir(parents=True, exist_ok=True)
    reveal_directory = root / "reveal" / dataset_version
    reveal_directory.mkdir(parents=True, exist_ok=True)
    metadata = pq.read_schema(spy).metadata or {}
    manifest = dict(**identity, dataset_version=dataset_version, target_id="SPY",
        downloaded_at="unknown; supplied locally by Aashna", audited_on="2026-11-08",
        base_date=base.date, base_value=100.0, base_close_usd=float(base.close_usd),
        supported_example_dates=DATES, assumptions=WARNINGS[:3] + (["At most 252 contiguous observed sessions; missing closes truncate the context, with no imputation."] if cpi_directory else WARNINGS[3:]),
        units=dict(close_usd="USD, split-adjusted only", level="first eligible close = 100",
                   cpi_percent="headline CPI-U seasonally adjusted month-on-month percent (0.2 means 0.2%)",
                   volume="split-adjusted shares", release_indicator="1 only on publication session"),
        source_metadata={k.decode(): v.decode() for k, v in metadata.items() if k != b"pandas"},
        rights=dict(reviewed_on="2026-11-08", ingestion="local academic/educational research",
                    public_demo="unreviewed; not enabled", redistribution="unreviewed; keep datasets local",
                    hf_terms="https://hfdatalibrary.com/pages/terms",
                    hf_download="https://hfdatalibrary.com/pages/download",
                    hf_dictionary="https://hfdatalibrary.com/pages/dictionary",
                    iex_terms="https://www.iex.io/legal/hist-data-terms",
                    bls="https://www.bls.gov/opub/copyright-information.htm",
                    nyse="https://www.nyse.com/publicdocs/ICE_NYSE_2025_Yearly_Trading_Calendar.pdf",
                    attribution="HF Data Library, Ahmed Elkassabgi; Data provided for free by IEX. CPI: U.S. Bureau of Labor Statistics. Calendar: NYSE/ICE; exchange_calendars."),
        audit=audit, calendar_validation=calendar_check, missing_inputs=[f"Original CPI publications before {releases.published_at.iloc[0][:10]}",
            "Analogue matching support is evaluated separately for each assumption and cutoff",
            "Historical delivery timestamps and point-in-time corporate-action vintages",
            "SPY before March 7, 2022 (including 2008)"])
    tables = {"spy_daily.parquet": history, "cpi_releases.parquet": releases,
              "sessions.parquet": schedule, "minute_gaps.parquet": gaps}
    for name, table in tables.items():
        table.to_parquet(directory / name, index=False)
    daily.to_parquet(reveal_directory / "spy_actuals.parquet", index=False)
    manifest["files"] = {name: digest(directory / name) for name in tables}
    manifest["reveal_sha256"] = digest(reveal_directory / "spy_actuals.parquet")
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (root / "processed" / "latest.txt").write_text(dataset_version + "\n")
    return directory, manifest


class MarketInputs:
    """Loads frozen historical inputs only. Has no reveal-reader dependency."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.manifest = json.loads((self.directory / "manifest.json").read_text())
        for name in ("spy_daily.parquet", "cpi_releases.parquet", "sessions.parquet"):
            if digest(self.directory / name) != self.manifest["files"][name]:
                raise UnsupportedInput(f"Processed file hash mismatch: {name}")
        self.prices = pd.read_parquet(self.directory / "spy_daily.parquet")
        self.releases = pd.read_parquet(self.directory / "cpi_releases.parquet")
        self.schedule = pd.read_parquet(self.directory / "sessions.parquet")

    def validate_segment(self, request, model_version):
        """Bind observed prefix to the snapshot; permit only contiguous simulated continuations."""
        seed = self.request(0.2, model_version)
        for key in ("target_id", "base_date", "base_value", "evidence_cutoff", "dataset_version", "model_version"):
            if getattr(request, key) != getattr(seed, key):
                raise UnsupportedInput(f"Unsupported {key}")
        size = len(seed.history)
        if request.history[:size] != seed.history:
            raise UnsupportedInput("Observed history differs from frozen snapshot")
        simulated = request.history[size:]
        if any(r.kind != "simulated" or r.available_at is not None or r.level <= 0 for r in simulated):
            raise UnsupportedInput("Only preceding simulated medians may extend frozen history")
        rows = [*simulated, *request.future]
        calendar = self.schedule[self.schedule.open > pd.Timestamp(request.evidence_cutoff)].date.tolist()
        if len(rows) > 65 or [r.date for r in rows] != calendar[:len(rows)]:
            raise UnsupportedInput("Require contiguous trading sessions within the 65-session horizon")
        previous = seed.history[-1].cpi_percent
        for row in rows:
            if not MIN_CPI <= row.cpi_percent <= MAX_CPI:
                raise UnsupportedInput("Monthly CPI assumption outside -2% to 2%")
            if row.release_indicator and row.date not in RELEASE_DATES:
                raise UnsupportedInput("Unsupported intervention date")
            if not row.release_indicator and row.cpi_percent != previous:
                raise UnsupportedInput("CPI may change only at an explicit release intervention")
            previous = row.cpi_percent
        return request

    def historical_rows(self, cutoff):
        cutoff = pd.Timestamp(cutoff)
        releases = self.releases[pd.to_datetime(self.releases.published_at) <= cutoff]
        if releases.empty:
            raise UnsupportedInput("No CPI vintage available at cutoff")
        prices = self.prices[pd.to_datetime(self.prices.available_at) <= cutoff]
        earliest = pd.Timestamp(releases.published_at.iloc[0])
        expected = self.schedule[(self.schedule.close >= earliest) & (self.schedule.close <= cutoff)]
        by_date = prices.set_index("date")
        missing = [i for i, d in enumerate(expected.date) if d not in by_date.index]
        if missing:
            expected = expected.iloc[missing[-1] + 1:]
        expected = expected.tail(252)
        rows = []
        previous_publication = None
        if not expected.empty:
            earlier = self.schedule[self.schedule.date < expected.date.iloc[0]]
            if not earlier.empty:
                prior = releases[pd.to_datetime(releases.published_at) <= earlier.close.iloc[-1]]
                if not prior.empty:
                    previous_publication = prior.published_at.iloc[-1]
        for session in expected.itertuples(index=False):
            if session.date not in by_date.index:
                raise UnsupportedInput(f"Missing close at {session.date}; no filling allowed")
            known = releases[pd.to_datetime(releases.published_at) <= session.close]
            release = known.iloc[-1]
            price = by_date.loc[session.date]
            rows.append(HistoryRow(date=session.date, level=float(price.level), kind="observed",
                available_at=price.available_at, cpi_percent=float(release.cpi_percent),
                release_indicator=int(release.published_at != previous_publication)))
            previous_publication = release.published_at
        if len(rows) < 20:
            raise UnsupportedInput("Missing close or CPI history: at least 20 contiguous sessions with known CPI are required")
        return rows

    def request(self, cpi_percent, model_version):
        if not math.isfinite(cpi_percent) or not MIN_CPI <= cpi_percent <= MAX_CPI:
            raise UnsupportedInput("Supported research assumption range is -2% to 2% monthly CPI")
        if self.manifest["cutoff"] != CUTOFF:
            raise UnsupportedInput("Only the frozen June 11 cutoff is implemented")
        cutoff = pd.Timestamp(self.manifest["cutoff"])
        rows = self.historical_rows(cutoff)
        future = self.schedule[self.schedule.open > cutoff].head(5).date.tolist()
        if future != DATES:
            raise UnsupportedInput("This loader supports only the frozen June 11 five-session example")
        return ForecastRequest(target_id="SPY", segment_id="june-cpi", base_date=self.manifest["base_date"],
            base_value=float(self.manifest["base_value"]), evidence_cutoff=self.manifest["cutoff"],
            dataset_version=self.manifest["dataset_version"], model_version=model_version, history=rows,
            future=[FutureRow(date=d, cpi_percent=float(cpi_percent), release_indicator=int(i == 0))
                    for i, d in enumerate(future)],
            assumptions=self.manifest["assumptions"] + [
                "June 11 release date is an explicit user-supplied scenario date.",
                "Hypothetical CPI replaces the June release, then carries across five sessions."])
