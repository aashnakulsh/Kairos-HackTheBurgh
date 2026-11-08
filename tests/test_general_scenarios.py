"""Focused general-scenario regression tests; no network, credentials or weights."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import io
import json
import unittest
import zipfile

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from api.app import create_app
from api.backend_errors import BackendError
from api.contracts import RunResponse
from api.scenario_contracts import ScenarioPlan, ScenarioDriver, NumericalPlan
from api.scenario_research import ScenarioResearcher, strict_schema
from api.settings import Settings
from training.scenario_adapter import MODEL_VERSION, ScenarioAdapter, driver_path
from data.scenario_market import ScenarioMarket
from data.scenario_events import EventArchive


class Market:
    version='invented-test-data';base_date='2024-01-01';base_value=100.0
    first_date='2024-01-01';last_date='2025-12-31'
    metadata={'DFF':{'name':'Rate','unit':'percent'}}
    def __init__(self,root):
        self.frame=pd.DataFrame({'date':pd.bdate_range(self.first_date,self.last_date).strftime('%Y-%m-%d'),
                                'level':100.,'DFF':3.})
    def align(self,day):return pd.bdate_range(day,periods=100).strftime('%Y-%m-%d').tolist()
    def context(self,day,cutoff=None):
        history=self.frame[self.frame.date<(cutoff or day)].tail(60).copy()
        if len(history)<20:raise ValueError('Need preceding history')
        return history,['DFF'],self.align(day)
    def catalog(self,day,cutoff=None):return {'features':{'DFF':self.metadata['DFF']},'effective_date':day,'limitations':[]}


class Adapter:
    model_version=MODEL_VERSION;engine='test-numerical-boundary'
    def __init__(self):self.calls=[];self.fail=False
    def forecast(self,history,future,features,segment_id):
        assert 'target' not in future and 'level' not in future
        if self.fail:raise ValueError('test failure')
        self.calls.append((history.copy(),future.copy()))
        values=float(history.level.iloc[-1])+np.cumsum(future.DFF.to_numpy()/100)
        return [dict(date=d,kind='simulated',value=float(v),q10=float(v-1),q90=float(v+1),engine=self.engine,segment_id=segment_id) for d,v in zip(future.date,values)]


def plan(day='2025-02-03',value=-.5):
    return ScenarioPlan(requested_date=day,effective_date=day,horizon_sessions=10,title='Unrestricted event title',
        hypothesis='Hypothetical event, not a coded CPI preset',drivers=[ScenarioDriver(feature='DFF',operation='add',value=value,
            transition_sessions=2,basis='llm_hypothesis',rationale='Explicit test hypothesis',source_urls=[])],
        explanation='Conditional test',sources=[],analogues=[],limitations=['Exploratory'],research_model='test',research_id='test',
        dataset_version=Market.version,web_search_used=True)


class Research:
    def __init__(self):self.calls=0;self.plan=plan();self.error=None
    def parse(self,request,run):
        self.calls+=1
        if self.error:raise self.error
        return self.plan


class GeneralTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.research=Research();self.adapter=Adapter()
        self.settings=Settings(app_mode='scenario',data_dir=Path(self.temp.name),sqlite_path=Path(self.temp.name)/'test.sqlite')
        with patch('api.scenario_backend.ScenarioMarket',Market):
            self.client=TestClient(create_app(self.settings,parser=self.research,adapter=self.adapter))
        self.addCleanup(self.client.close)
        self.run=self.client.post('/api/timelines',json={'target_id':'SPY','request_id':'create'}).json()
        self.url='/api/timelines/'+self.run['timeline_id']
    def submit(self,selected=None):
        draft=self.client.post(self.url+'/interpret',json=dict(text='An arbitrary political scenario',mode='replace' if selected else 'add',
            selected_prompt_id=selected,expected_revision=self.run['revision'])).json()
        self.assertEqual(draft['status'],'ready',draft)
        request=dict(draft_id=draft['draft_id'],expected_revision=self.run['revision'],request_id='r'+str(self.run['revision']))
        response=self.client.post(self.url+'/commit',json=request)
        if 'revision' in response.json():self.run=response.json()
        return response,request
    def test_general_dates_baseline_edit_replay_and_retry(self):
        response,body=self.submit();self.assertEqual(response.status_code,200)
        first=deepcopy(self.run);RunResponse.model_validate(first)
        self.assertNotEqual(first['series']['points'],first['baseline']['points'])
        self.assertEqual(first['prompts'][0]['operation'],'scenario')
        self.assertEqual(first['prompts'][0]['effective_start'],'2025-02-03')
        self.research.plan=plan('2025-02-17',.2);self.submit()
        self.research.plan=plan(value=-1.0);self.submit('p1')
        self.assertEqual([p['id'] for p in self.run['prompts']],['p1','p2'])
        before=deepcopy(self.run);count=self.research.calls
        self.research.plan=plan(value=-1.0);self.submit('p1')
        self.assertEqual(before['series'],self.run['series'])
        self.assertEqual(self.research.calls,count+1)
        self.assertEqual(self.client.get(self.url+'/revisions/1').json(),first)
        count=len(self.adapter.calls)
        self.assertEqual(self.client.post(self.url+'/commit',json=body).json(),first)
        self.assertEqual(len(self.adapter.calls),count)
        actual=self.client.get(self.url+f'/revisions/{self.run["revision"]}/reveal').json()
        self.assertTrue(all(p['value']==100 for p in actual['series']['points']))
        self.assertEqual(self.client.get(self.url).json(),self.run)
        cutoff=self.run['evidence_cutoff'][:10]
        for history,_ in self.adapter.calls:
            observed=history[history.date<cutoff]
            self.assertTrue((observed.level==100).all())
    def test_provider_and_forecast_errors_preserve_state(self):
        self.submit();before=deepcopy(self.run)
        self.research.error=BackendError(200,'needs_clarification','ambiguous','Specify the date')
        response=self.client.post(self.url+'/interpret',json=dict(text='Ambiguous date',mode='replace',selected_prompt_id='p1',expected_revision=1))
        self.assertEqual(response.json()['status'],'needs_clarification')
        self.research.error=None;self.adapter.fail=True
        response,_=self.submit('p1');self.assertEqual(response.status_code,503)
        self.assertEqual(self.client.get(self.url).json(),before)
    def test_driver_duration_and_numeric_units(self):
        driver=ScenarioDriver(feature='DFF',operation='add',value=-.5,transition_sessions=2,duration_sessions=3,
            recovery_sessions=2,basis='user_assumption',rationale='Explicit',source_urls=[])
        np.testing.assert_allclose(driver_path(driver,3.,6),[2.75,2.5,2.5,2.75,3.,3.])
    def test_chronos_frames_are_real_covariates_never_target_injection(self):
        class Pipeline:
            def predict_df(inner,past,future_df,**kwargs):
                self.assertEqual(past.DFF.tolist(),[3.,3.1]);self.assertEqual(future_df.DFF.tolist(),[2.8,2.7])
                self.assertNotIn('target',future_df)
                out=future_df[['item_id','timestamp']].copy()
                out['0.1']=99.;out['0.5']=100.;out['0.9']=101.
                return out
        history=pd.DataFrame({'level':[100.,101.],'DFF':[3.,3.1]})
        future=pd.DataFrame({'date':['2025-03-03','2025-03-04'],'DFF':[2.8,2.7]})
        self.assertEqual(len(ScenarioAdapter(Pipeline()).forecast(history,future,['DFF'],'p1')),2)
        with self.assertRaises(ValueError):ScenarioAdapter(Pipeline()).forecast(history,future.assign(target=123),['DFF'],'p1')
    def test_live_research_requires_web_search_and_strict_feature_schema(self):
        numerical=dict(drivers=[plan().drivers[0].model_dump()],explanation='test',limitations=[])
        calls=[]
        def transport(request,timeout):
            payload=json.loads(request.data);calls.append(payload)
            result={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(numerical)}]}]}
            return io.BytesIO(json.dumps(result).encode())
        settings=Settings(app_mode='scenario',data_dir=Path(self.temp.name),openai_api_key='test',openai_model='test')
        researcher=ScenarioResearcher(settings,Market(''),transport=transport)
        researcher.call('scenario extraction',{},NumericalPlan,features=['DFF'])
        schema=calls[0]['text']['format']['schema']
        self.assertEqual(schema['$defs']['ScenarioDriver']['properties']['feature']['enum'],['DFF'])
        with self.assertRaises(BackendError):researcher.call('research',{},NumericalPlan,search=True)
        self.assertEqual(calls[-1]['tool_choice'],'required')

    def test_observation_cutoff_missing_history_and_weekend_future(self):
        market=ScenarioMarket.__new__(ScenarioMarket)
        market.metadata={'DFF':{}}
        days=pd.bdate_range('2025-01-01','2025-03-07').strftime('%Y-%m-%d')
        market.frame=pd.DataFrame({'date':days,'level':100.,'DFF':3.})
        market.align=lambda day:pd.bdate_range(day,periods=100).strftime('%Y-%m-%d').tolist()
        history,features,_=market.context('2025-03-03')
        self.assertLess(history.date.max(),'2025-03-03')
        self.assertEqual(features,['DFF'])
        # Future covariates/targets cannot leak through the cutoff.
        market.frame.loc[market.frame.date>='2025-03-03',['level','DFF']]=999.
        self.assertTrue(history.equals(market.context('2025-03-03')[0]))
        self.assertIsNone(market.analogue('2025-02-24','2025-03-03',10))
        self.assertIsNotNone(market.analogue('2025-02-03','2025-03-03',10))
        # A weekend must not bypass missing preceding observations.
        with self.assertRaises(ValueError):market.context('2025-03-22','2025-03-22')
        market.frame.loc[market.frame.date=='2025-02-26','level']=np.nan
        with self.assertRaises(ValueError):market.context('2025-03-03')

    def test_gdelt_uses_row_event_date_not_just_archive_date(self):
        archive=EventArchive(self.temp.name,transport=lambda *a,**k:self.fail('Network should not run'))
        rows=[]
        for day in ['20240402','20250402']:
            row=['']*58;row[0]='test-'+day;row[1]=day;row[-1]='https://example.org/'+day
            rows.append('\t'.join(row))
        with zipfile.ZipFile(archive.root/'20250402.export.CSV.zip','w') as file:
            file.writestr('events.CSV','\n'.join(rows))
        records=archive.events('2025-04-02','2025-06-01')
        self.assertEqual([r['record_id'] for r in records],['test-20250402'])
        self.assertEqual(archive.events('2025-04-02','2025-04-02'),[])

if __name__=='__main__':unittest.main()
