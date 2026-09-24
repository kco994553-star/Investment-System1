from pathlib import Path
import importlib.util, os, tempfile

def load():
 p=Path(__file__).parents[1]/'tools'/'fetch_krx_data.py'; s=importlib.util.spec_from_file_location('fetch_krx_data',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def test_krx_runner_requires_env_secret():
 m=load(); old=os.environ.pop('KRX_AUTH_KEY',None)
 try:
  try: m.run(Path(tempfile.mkdtemp()),'20260923',['kospi_daily'])
  except RuntimeError as e: assert 'KRX_AUTH_KEY' in str(e)
  else: assert False
 finally:
  if old is not None: os.environ['KRX_AUTH_KEY']=old

def test_krx_endpoint_contract_and_no_secret_in_url():
 m=load(); assert m.ENDPOINTS['kospi_daily'][0]=='sto/stk_bydd_trd'; assert m.ENDPOINTS['kosdaq_daily'][0]=='sto/ksq_bydd_trd'; assert 'AUTH_KEY' not in m.BASE
