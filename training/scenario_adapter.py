"""General measured-covariate conditioning of the pinned Chronos-2 model.

No narrative -> SPY multiplier, target injection or synthetic forecast fallback.
"""
from threading import Lock
import numpy as np
import pandas as pd
from training.chronos_adapter import ChronosAdapter, REVISION

MODEL_VERSION = f'chronos-2-2.3.2-{REVISION[:12]}-scenario-v1'


class ScenarioAdapter:
    model_version = MODEL_VERSION
    engine = 'chronos-2-scenario-cpu'

    def __init__(self, pipeline=None):
        self.loader = ChronosAdapter(None, pipeline=pipeline)
        self.lock = Lock()

    def forecast(self, history, future, features, segment_id):
        if 'level' in future or 'target' in future:
            raise ValueError('Future market targets must never be provided to Chronos')
        clock = pd.date_range('2000-01-01', periods=len(history)+len(future),freq='D')
        past = pd.DataFrame({'item_id':'SPY','timestamp':clock[:len(history)],'target':history.level.to_numpy()})
        next_frame = pd.DataFrame({'item_id':'SPY','timestamp':clock[len(history):]})
        for feature in features:
            past[feature] = history[feature].to_numpy(dtype=float)
            next_frame[feature] = future[feature].to_numpy(dtype=float)
        if not np.isfinite(past[['target',*features]].to_numpy()).all() or not np.isfinite(next_frame[features].to_numpy()).all():
            raise ValueError('Numerical model inputs must be finite')
        with self.lock:
            output = self.loader._load().predict_df(past,future_df=next_frame,
                prediction_length=len(future),context_length=len(history),quantile_levels=[.1,.5,.9],
                cross_learning=False,id_column='item_id',timestamp_column='timestamp',target='target')
        output = output.sort_values('timestamp')
        if output.timestamp.tolist()!=next_frame.timestamp.tolist() or set(output.item_id)!={'SPY'}:
            raise ValueError('Forecast dates/target do not match the requested inputs')
        quantiles=output[['0.1','0.5','0.9']].to_numpy(dtype=float)
        if not np.isfinite(quantiles).all() or (np.diff(quantiles,axis=1)<0).any() or (quantiles[:,1]<=0).any():
            raise ValueError('Chronos produced invalid quantiles')
        return [dict(date=day,kind='simulated',value=float(q[1]),q10=float(q[0]),q90=float(q[2]),
                     engine=self.engine,segment_id=segment_id) for day,q in zip(future.date,quantiles)]


def driver_path(driver, baseline, length):
    """Interpolate explicit scenario assumptions in feature units, never stock prices."""
    if driver.operation=='set': endpoint=driver.value
    elif driver.operation=='add': endpoint=baseline+driver.value
    elif driver.operation=='multiply': endpoint=baseline*driver.value
    else: raise ValueError('Unknown feature operation')
    ramp = np.minimum((np.arange(length)+1)/driver.transition_sessions,1.0)
    if driver.duration_sessions is not None:
        if driver.recovery_sessions:
            recovery = np.maximum(0.0,1.0-np.maximum(np.arange(length)+1-driver.duration_sessions,0)/driver.recovery_sessions)
        else:
            recovery = (np.arange(length)<driver.duration_sessions).astype(float)
        ramp *= recovery
    return baseline+(endpoint-baseline)*ramp
