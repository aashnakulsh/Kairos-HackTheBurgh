"""Versioned scenario context assembled from actual local observations.

No future target rows enter context. FRED exports are current vintages: observation
lag is explicit and is not a claim of verified historical publication availability.
"""
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data.real_market import audit_prices, digest, parse_release, sessions

FRED_META = {
    'DFF': ('Federal funds effective rate', 'percent'),
    'DCOILWTICO': ('WTI oil price', 'USD/barrel'),
    'VIXCLS': ('VIX', 'index'),
}


class ScenarioMarket:
    def __init__(self, root):
        self.root = Path(root)
        price_path = self.root / 'raw/hf/SPY_raw_1min.parquet'
        fred_paths = sorted((self.root / 'raw/fred').glob('*.csv'))
        if not fred_paths:
            raise ValueError('Add FRED CSV observations to data/local/raw/fred')
        bls = {p.stem: p for folder in ['bls', 'bls-expanded']
               for p in (self.root / 'raw' / folder).glob('cpi_*') if p.suffix in {'.txt', '.htm'}}
        self.sources = {str(p.relative_to(self.root)): digest(p) for p in [price_path, *fred_paths, *bls.values()]}
        self.version = 'scenario-' + sha256(json.dumps(self.sources, sort_keys=True).encode()).hexdigest()[:20]
        directory = self.root / 'processed' / self.version
        cache = directory / 'market.parquet'
        self.metadata = {p.stem: dict(name=FRED_META.get(p.stem, (p.stem, 'source units'))[0],
            unit=FRED_META.get(p.stem, (p.stem, 'source units'))[1],
            source_url='https://fred.stlouisfed.org/series/' + p.stem) for p in fred_paths}
        if bls:
            self.metadata['CPI_MOM'] = dict(name='Headline monthly CPI-U, seasonally adjusted', unit='percent', source_url='https://www.bls.gov/cpi/')
        if cache.exists():
            self.frame = pd.read_parquet(cache)
        else:
            raw = pd.read_parquet(price_path)
            start, end = raw.datetime.min().strftime('%Y-%m-%d'), raw.datetime.max().strftime('%Y-%m-%d')
            calendar = sessions(start, end)
            daily, _, _ = audit_prices(raw, calendar)
            daily['level'] = 100 * daily.close_usd / daily.close_usd.iloc[0]
            # Retain missing target sessions explicitly. Never compress missing time.
            frame = calendar[['date', 'open', 'close']].merge(daily[['date','level','available_at']], on='date', how='left')
            for path in fred_paths:
                values = pd.read_csv(path, na_values=['.', ''])
                if list(values.columns) != ['observation_date', path.stem]:
                    raise ValueError(f'Expected observation_date,{path.stem} in {path.name}')
                values[path.stem] = pd.to_numeric(values[path.stem], errors='raise')
                if values.observation_date.duplicated().any():
                    raise ValueError(f'Duplicate observation dates in {path.name}')
                # Two calendar days of lag; carry only prior observations <=7 days old.
                # All such carries/lag/current-vintage limitations are disclosed.
                values['usable_date'] = pd.to_datetime(values.observation_date) + pd.Timedelta(days=2)
                left = pd.DataFrame({'usable_date':pd.to_datetime(frame.date)})
                joined = pd.merge_asof(left, values.dropna(subset=[path.stem]).sort_values('usable_date'),
                                       on='usable_date', direction='backward', tolerance=pd.Timedelta(days=7))
                frame[path.stem] = joined[path.stem].to_numpy()
            if bls:
                releases = pd.DataFrame([parse_release(p) for p in bls.values()]).sort_values('published_at')
                # Observed CPI is available at each historical session's close.
                released = pd.DataFrame({'instant':pd.to_datetime(releases.published_at,utc=True).astype('datetime64[ns, UTC]'), 'CPI_MOM':releases.cpi_percent})
                frame['CPI_MOM'] = pd.merge_asof(pd.DataFrame({'instant':pd.to_datetime(frame.close,utc=True)}), released, on='instant',direction='backward',tolerance=pd.Timedelta(days=45))['CPI_MOM'].to_numpy()
            self.frame = frame
            directory.mkdir(parents=True, exist_ok=True)
            frame.to_parquet(cache,index=False)
            (directory/'manifest.json').write_text(json.dumps(dict(dataset_version=self.version,sources=self.sources,
                policy='scenario-context-v1; FRED current vintage, two-calendar-day lag, prior carry max7days; BLS release-asof'),indent=2))
        self.base_date = self.frame.date.iloc[0]
        self.base_value = 100.0
        self.first_date, self.last_date = self.frame.date.iloc[0], self.frame.date.iloc[-1]

    def align(self, requested):
        # Future sessions are calendar-only; never fabricated observed target rows.
        grid = sessions(requested, (pd.Timestamp(requested)+pd.Timedelta(days=130)).strftime('%Y-%m-%d'))
        return grid.date.tolist()

    def context(self, requested, cutoff=None):
        grid = self.align(requested)
        effective = grid[0]
        cutoff = cutoff or effective
        history = self.frame[self.frame.date < cutoff].tail(252).copy()
        missing = history.index[history.level.isna()]
        if len(missing): history = history.loc[missing[-1]+1:]
        if len(history) < 20:
            raise ValueError('At least 20 contiguous observed market sessions before the scenario date are required')
        # A future scenario may start on the next session, but cannot skip unknown history.
        expected = self.align(history.date.iloc[-1])[1]
        if expected != self.align(cutoff)[0]:
            raise ValueError('The chosen date is beyond available preceding market history')
        available = [key for key in self.metadata if history[key].notna().all()]
        if not available:
            raise ValueError('No complete numeric conditioning series for this context')
        return history, available, grid

    def catalog(self, requested, cutoff=None):
        history, available, grid = self.context(requested, cutoff)
        return dict(effective_date=grid[0], historical_sessions=len(history), last_observation=history.date.iloc[-1],
            features={key:dict(**self.metadata[key], last_value=float(history[key].iloc[-1]),
                minimum=float(history[key].min()),maximum=float(history[key].max())) for key in available},
            missing_features=[k for k in self.metadata if k not in available],
            limitations=['FRED files are current vintages, not ALFRED vintage data.',
                'FRED observations lagged two calendar days and prior values carried at most seven days; publication times unverified.',
                'SPY is IEX-only adjusted-price history; no causal identification.'])

    def analogue(self, event_date, cutoff, horizon=20):
        start = self.frame[self.frame.date >= event_date].index
        if not len(start): return None
        i = start[0]
        if i < 1: return None
        window = self.frame.loc[i:i+horizon-1]
        before = self.frame.loc[i-1]
        if len(window) != horizon or window.date.iloc[-1] >= cutoff or window.level.isna().any() or pd.isna(before.level):
            return None
        returns = window.level.to_numpy()/float(before.level)-1
        daily = np.diff(np.r_[float(before.level),window.level.to_numpy()])/np.r_[float(before.level),window.level.to_numpy()[:-1]]
        drivers = {}
        for key in self.metadata:
            if pd.notna(before[key]) and window[key].notna().all():
                drivers[key] = dict(start=float(before[key]),end=float(window[key].iloc[-1]),
                                    change=float(window[key].iloc[-1]-before[key]))
        return dict(event_date=event_date,effective_date=window.date.iloc[0],end_date=window.date.iloc[-1],
            sessions=horizon,market_return_percent=float(returns[-1]*100),
            realized_daily_volatility_percent=float(np.std(daily)*100),
            worst_close_return_percent=float(returns.min()*100),feature_changes=drivers,
            method='Observed SPY/FRED window; association, not attributed causal effect')
