"""General scenario runtime using the existing durable timeline transactions."""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from api.backend_errors import BackendError
from api.contracts import Instruction, Prompt, RunResponse, RevealResponse
from api.scenario_research import ScenarioResearcher
from data.scenario_market import ScenarioMarket
from training.scenario_adapter import ScenarioAdapter, MODEL_VERSION, driver_path

LABEL='Exploratory SPY scenarios — researched events, historical data and conditional Chronos forecasts'


class ScenarioBackend:
    label=LABEL
    def __init__(self, settings, adapter=None, researcher=None):
        self.market=ScenarioMarket(settings.data_dir)
        self.adapter=adapter or ScenarioAdapter()
        self.researcher=researcher or ScenarioResearcher(settings,self.market)
        self.warnings=['Hypothetical numerical assumptions are not observed facts or established causal effects.',
            'Current-vintage data and model pretraining prevent claims of a leakage-free historical backtest.',
            'Known data channels are not a whitelist of permitted event prompts. Missing channels are disclosed.']
        self.corpus_version='scenario-research-v1'

    def capabilities(self):
        return dict(contract_version='1',mode='live',data_label=LABEL,targets=['SPY'],unit='index',frequency='trading_session',
            default_viewport=dict(start_year=int(self.market.first_date[:4]),end_year=int(self.market.last_date[:4])),
            coverage=dict(first_session=self.market.first_date,last_session=self.market.last_date,gaps=[]),
            supported_event_families=['open_ended_scenario'],default_horizon_sessions=20,max_horizon_sessions=65,
            max_prompts=3,evidence_available=True,display_rights='Local research data; see source manifests for display/redistribution terms.',fixture_presets=[])

    def empty(self, timeline_id):
        # No date is assumed before the user supplies a scenario.
        return RunResponse(contract_version='1',data_label=LABEL,timeline_id=timeline_id,run_id=None,
            dataset_version=self.market.version,model_version=MODEL_VERSION,corpus_version=self.corpus_version,
            request_id=None,revision=0,parent_revision=None,changed_from=None,replace_through=None,
            series_mode='full',evidence_cutoff=None,prompts=[],panels={},
            series=dict(target_id='SPY',base_date=self.market.base_date,base_value=100.0,unit='index',frequency='trading_session',points=[])).model_dump()

    def compatible(self, run):
        if run['dataset_version']!=self.market.version or run['model_version']!=MODEL_VERSION:
            raise BackendError(409,'conflict','timeline_configuration_mismatch','Create a new scenario timeline for the current data/model; old revisions remain readable.',run['revision'])

    def interpret(self, run, request):
        if request.mode=='add' and len(run['prompts'])>=3:
            raise BackendError(200,'unsupported','prompt_limit','Replace an existing prompt; this workspace supports three events.',run['revision'])
        plan=self.researcher.parse(request,run)
        return Instruction(date_precision='day',requested_start=plan.requested_date,requested_end=None,
            effective_start=plan.effective_date,effective_end=None,effective_at=datetime.fromisoformat(plan.effective_date+'T09:30:00').replace(tzinfo=ZoneInfo('America/New_York')).isoformat(),
            timezone='America/New_York',scope='event',release_dates=[],operation='scenario',value=None,unit='scenario',reference=None,scenario=plan)

    def candidate(self, old, draft, request_id, adapter):
        self.compatible(old)
        instruction=draft.instruction
        if instruction.scenario is None or instruction.scenario.dataset_version!=self.market.version:
            raise BackendError(409,'conflict','scenario_plan_mismatch','Reinterpret this scenario against current data',old['revision'])
        prompts=deepcopy(old['prompts'])
        previous=next((p for p in prompts if p['id']==draft.selected_prompt_id),None)
        number=previous['display_number'] if previous else len(prompts)+1
        if number>3:raise BackendError(200,'unsupported','prompt_limit','Three active events are supported',old['revision'])
        current=Prompt(**instruction.model_dump(),id=previous['id'] if previous else f'p{number}',display_number=number,
            creation_order=number,text=draft.text,evidence_ids=[],resolved_value=None,status='supported').model_dump()
        prompts=sorted([p for p in prompts if p['id']!=current['id']]+[current],key=lambda p:(p['effective_start'],p['creation_order']))
        first=prompts[0]['effective_start']
        cutoff=min(first,old['evidence_cutoff'][:10]) if old['evidence_cutoff'] else first
        try:
            history,features,grid=self.market.context(first,cutoff)
            grid=self.market.align(cutoff)
            end=max(grid.index(p['effective_start'])+p['scenario']['horizon_sessions'] for p in prompts)
        except (ValueError,IndexError) as exc:
            raise BackendError(200,'unsupported','data_coverage',str(exc),old['revision']) from exc
        if end>65:raise BackendError(200,'unsupported','horizon_coverage','The combined timeline exceeds 65 trading sessions; move events closer or shorten the horizon.',old['revision'])
        days=grid[:end]
        baseline_inputs=pd.DataFrame({'date':days})
        for key in features:baseline_inputs[key]=float(history[key].iloc[-1])
        scenario_inputs=baseline_inputs.copy()
        warnings=list(self.warnings)
        for p in prompts:
            start=days.index(p['effective_start'])
            from api.scenario_contracts import ScenarioPlan
            plan=ScenarioPlan.model_validate(p['scenario'])
            if any(d.feature not in features for d in plan.drivers):
                raise BackendError(200,'needs_clarification','missing_conditioning_history','An event needs a feature unavailable at the frozen cutoff. Start a new timeline or refine it.',old['revision'])
            for driver in plan.drivers:
                initial=float(scenario_inputs[driver.feature].iloc[start-1]) if start else float(history[driver.feature].iloc[-1])
                values=driver_path(driver,initial,len(days)-start)
                if driver.feature in {'VIXCLS'} and (values<0).any():
                    raise BackendError(200,'needs_clarification','invalid_feature_level','Volatility-index levels cannot be negative.',old['revision'])
                scenario_inputs.loc[start:,driver.feature]=values
                observed=history[driver.feature]
                if values.min()<observed.min() or values.max()>observed.max():
                    warnings.append(f'{p["id"]}: {driver.feature} assumption extends outside the supplied context range; extrapolation.')
            warnings.extend(plan.limitations)
        def infer(future):
            rolling=history.copy(); points=[]
            # Same fixed blocks for baseline, scenario, add and edit.
            for offset in range(0,len(future),5):
                block=future.iloc[offset:offset+5].reset_index(drop=True)
                try:prediction=adapter.forecast(rolling.tail(252),block,features,prompts[0]['id'])
                except Exception as exc:
                    raise BackendError(503,'unavailable','scenario_forecast_failed','Chronos inference failed; saved revision is unchanged.',old['revision']) from exc
                for point in prediction:
                    active=next((p for p in reversed(prompts) if p['effective_start']<=point['date']),prompts[0])
                    point['segment_id']=active['id']
                points+=prediction
                extension=block.copy();extension['level']=[p['value'] for p in prediction]
                rolling=pd.concat([rolling,extension],ignore_index=True)
            return points
        numerical=infer(scenario_inputs); baseline=infer(baseline_inputs)
        observed=[dict(date=row.date,kind='observed',value=float(row.level),q10=None,q90=None,engine=None,segment_id=None) for row in history.itertuples()]
        panels={}
        for p in prompts:
            plan=p['scenario']
            selected=[r for r in numerical if r['segment_id']==p['id']]
            comparable=[r for r in baseline if r['segment_id']==p['id']]
            evidence=[]
            for source in plan['sources']:
                day=source['publication_date']
                try:
                    if day is None or pd.Timestamp(day).date().isoformat()>=cutoff:continue
                    instant=pd.Timestamp(day).date().isoformat()+'T00:00:00Z'
                except (ValueError,TypeError):continue
                evidence.append(dict(id='web-'+sha256(source['url'].encode()).hexdigest()[:12],title=source['title'],
                    url=source['url'],publication_time=instant,passage_locator=source['excerpt']))
            evidence=list({e['id']:e for e in evidence}.values())
            p['evidence_ids']=[e['id'] for e in evidence]
            comparison=(f'Final scenario median {selected[-1]["value"]:.4f}; baseline median {comparable[-1]["value"]:.4f} index. '
                        'Baseline holds observed covariates constant; both paths use Chronos.') if selected else 'Superseded before producing an active segment.'
            panels[p['id']]=dict(summary=plan['explanation'],hypotheses=[],evidence=evidence,impacts=[],
                horizon=' '.join(dict.fromkeys(warnings+['Uncalibrated conditional model quantiles; later bands condition on preceding simulated medians.'])),
                comparison=comparison,engine=adapter.engine,support_count=len(plan['analogues']),status='supported')
        run=deepcopy(old)
        run.update(revision=old['revision']+1,parent_revision=old['revision'],run_id=f'{old["timeline_id"]}-run-{old["revision"]+1}',
            request_id=request_id,changed_from=cutoff,replace_through=max([days[-1]]+[p['date'] for p in old['series']['points']]),
            evidence_cutoff=cutoff+'T00:00:00Z',series_mode='full',prompts=prompts,panels=panels,scenario_warnings=list(dict.fromkeys(warnings)))
        run['series']['points']=observed+numerical
        run['baseline']=dict(run['series'],points=observed+baseline)
        RunResponse.model_validate(run)
        return run,deepcopy(run)

    def reveal(self, run):
        dates={p['date'] for p in run['series']['points'] if p['kind']=='simulated'}
        available=self.market.frame[self.market.frame.date.isin(dates)]
        actual={r.date:r.level for r in available.itertuples()}
        points=[dict(date=d,kind='observed' if pd.notna(actual.get(d)) else 'gap',value=float(actual[d]) if pd.notna(actual.get(d)) else None,
                     q10=None,q90=None,engine=None,segment_id=None) for d in sorted(dates)]
        return RevealResponse(timeline_id=run['timeline_id'],revision=run['revision'],data_label='Actual observations, excluded from scenario inference',
            series=dict(run['series'],points=points),sources=[],attribution='IEX-only SPY history; missing/unobserved dates remain gaps.').model_dump()
