"""Run the general researched-scenario API with local data and server-side credentials."""
import argparse
import os
from pathlib import Path
import sys
from time import time_ns
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.serve_research import load_provider_env


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file',type=Path)
    p.add_argument('--data-dir',type=Path,default=Path('data/local'))
    p.add_argument('--database',type=Path)
    p.add_argument('--model')
    p.add_argument('--port',type=int,default=8772)
    args=p.parse_args()
    if args.env_file:load_provider_env(args.env_file)
    if args.model:os.environ['OPENAI_MODEL']=args.model
    os.environ.update(APP_MODE='scenario',DATA_DIR=str(args.data_dir.resolve()),
        SQLITE_PATH=str((args.database or args.data_dir/f'scenarios-{time_ns()}.sqlite').resolve()),
        HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',FORECAST_DEVICE='cpu',PARSER_PROVIDER='auto')
    if not os.environ.get('OPENAI_API_KEY') or not os.environ.get('OPENAI_MODEL'):
        p.error('Set server-side OPENAI_API_KEY and OPENAI_MODEL; never put keys in Vite')
    from api.app import create_app
    from api.settings import Settings
    import uvicorn
    settings=Settings();app=create_app(settings)
    print(f'Scenario API: http://127.0.0.1:{args.port}; model={settings.openai_model}; database={settings.sqlite_path}',flush=True)
    uvicorn.run(app,host='127.0.0.1',port=args.port)

if __name__=='__main__':main()
