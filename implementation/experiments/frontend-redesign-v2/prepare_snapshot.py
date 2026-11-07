"""Build a fixed, price-free design snapshot from explicitly downloaded public files.
No network requests, credentials, private holdings, or production outputs are used.
Usage: python prepare_snapshot.py PUBLIC_INPUT_DIR QGV2_JSON
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
inputs = Path(sys.argv[1])
qfile = Path(sys.argv[2])
qgv = json.loads(qfile.read_text())

def load(name):
    return json.loads((inputs / name).read_text())

catalog = load('actual-catalog.json')
classification = load('company-classification.json')
types = load('company-types-pricefree.json')
disclosures = load('sec-disclosures.json')
news = load('news-signals.json')

info = {
 'NVDA': ['nvda','NVIDIA','엔비디아','AI·가속 컴퓨팅 플랫폼','AI and accelerated computing'],
 'AMD': ['amd','Advanced Micro Devices','에이엠디 AMD','CPU·GPU와 데이터센터 반도체','CPUs, GPUs and data center semiconductors'],
 'MSFT': ['msft','Microsoft','마이크로소프트','클라우드·기업용 소프트웨어','Cloud and enterprise software'],
 'GOOGL': ['googl','Alphabet','알파벳 구글','검색·광고·클라우드','Search, advertising and cloud'],
 'AMZN': ['amzn','Amazon','아마존','전자상거래·클라우드','E-commerce and cloud'],
 'ASML': ['asml','ASML Holding','에이에스엠엘','반도체 노광 장비','Semiconductor lithography'],
 'LRCX': ['lrcx','Lam Research','램리서치 램리서치','반도체 식각·증착 장비','Semiconductor etch and deposition'],
 'KLAC': ['klac','KLA','케이엘에이','반도체 검사·계측 장비','Semiconductor inspection and metrology'],
 'AVGO': ['avgo','Broadcom','브로드컴','반도체·인프라 소프트웨어','Semiconductors and infrastructure software'],
 'QCOM': ['qcom','Qualcomm','퀄컴','모바일·무선통신 반도체','Mobile and wireless semiconductors'],
 'INTC': ['intc','Intel','인텔','프로세서·반도체 제조','Processors and semiconductor manufacturing'],
 'RTX': ['rtx','RTX','알티엑스 레이시온','항공우주·방위산업','Aerospace and defense'],
 'SYK': ['stry','Stryker','스트라이커','정형외과·수술 의료기기','Orthopedics and surgical devices'],
 'ETN': ['etn','Eaton','이튼','전력 관리·전기 장비','Power management and electrical equipment'],
 'HUBB': ['hubb','Hubbell','허벨','전력망·전기 인프라','Grid and electrical infrastructure'],
 'GEV': ['gev','GE Vernova','지이 버노바','발전·전력망·풍력','Power generation, grids and wind'],
 'ROK': ['rok','Rockwell Automation','로크웰 오토메이션','산업 자동화·제어','Industrial automation and control'],
 '8035': ['tokyo_electron','Tokyo Electron','도쿄일렉트론 TEL','반도체 제조 장비','Semiconductor production equipment'],
 '042700': ['hanmi','Hanmi Semiconductor','한미반도체','반도체 패키징 장비','Semiconductor packaging equipment']
}
names = {'ABNB':'Airbnb','ADI':'Analog Devices','AXON':'Axon Enterprise','COIN':'Coinbase','DPZ':"Domino’s Pizza",'EQIX':'Equinix','FANG':'Diamondback Energy','FSLR':'First Solar','MDLZ':'Mondelez','NDAQ':'Nasdaq','ROST':'Ross Stores','SBUX':'Starbucks','VRSK':'Verisk','WBD':'Warner Bros. Discovery','WMT':'Walmart','AIZ':'Assurant','AMT':'American Tower','AON':'Aon','APH':'Amphenol','BLK':'BlackRock','BXP':'BXP','CB':'Chubb','CHD':'Church & Dwight','CMG':'Chipotle','AAPL':'Apple','TSLA':'Tesla','META':'Meta Platforms'}
target = {x['ticker']:x for x in catalog['instruments']}
def clean(ticker, code, row):
    i=info.get(ticker,[None,names.get(ticker,ticker),'','',''])
    cid=i[0]
    cl=classification['data']['companies'].get(cid,{})
    tp=types['data']['companies'].get(cid,{})
    return {'ticker':ticker,'code':code,'id':cid,'name':i[1],'alias':i[2],
      'about':i[3],'aboutEn':i[4],'target':target.get(ticker,{}).get('target_units',0)/100,
      'allocationTheme':target.get(ticker,{}).get('theme_id'),
      'record':{k:row.get(k) for k in ['state','acquired_at','calc_version','axes','factors','metrics','fiscal_year_end','reason_codes','sic','profile']},
      'history':row.get('v_inputs_v2',{}).get('operating_margin_history',[]) if row.get('v_inputs_v2') else [],
      'classification':cl,'types':tp.get('memberships',{}),'typesAsOf':types['as_of']}
rows=[]
for code,r in qgv['records'].items():
    ticker=code.split(':',1)[1]
    # Target and universe inputs can have different acquisition timestamps. Prefer the explicitly captured target row only for target companies; record its source.
    cid=info.get(ticker,[None])[0]
    selected=qgv['target'].get(cid,r)
    row=clean(ticker,code,selected)
    row['recordSource']='target' if cid in qgv['target'] else 'universe'
    rows.append(row)
existing={r['ticker'] for r in rows}
for ticker in target:
    if ticker not in existing:
        cid=info[ticker][0]
        row=clean(ticker,('KRX:' if ticker=='042700' else 'TYO:')+ticker,qgv['target'].get(cid,{}))
        row['recordSource']='target';rows.append(row)
lookup={v[0]:k for k,v in info.items()}
articles=[]
for e in disclosures['events']:
    articles.append({'kind':'filing','ticker':lookup.get(e['company_id'],e['company_id'].upper()),'title':e['form']+' · '+', '.join(e.get('items',[])),'source':'SEC','at':e.get('accepted_at') or e.get('filing_date'),'occurrence':e.get('occurrence'),'url':e.get('link'),'classification':e.get('classification')})
for e in news['items']:
    articles.append({'kind':'news','ticker':lookup.get(e['company_id'],e['company_id'].upper()),'title':e['title'],'source':e['source'],'at':e['published_at'],'occurrence':e.get('occurrence'),'url':e['link'],'classification':e.get('classification')})
articles.sort(key=lambda x:x['at'] or '',reverse=True)
payload={'schema':'investment-ui-design/2','capturedAt':datetime.now(timezone.utc).isoformat(),'asOf':qgv['as_of'],'calcVersion':qgv['calc_version'],'qgvSha256':hashlib.sha256(qfile.read_bytes()).hexdigest(),'universeCount':qgv['code_count'],'rows':rows,'articles':articles,'themes':catalog['themes'],'targetVersion':catalog['target_root_version'],'universeAxes':[{'calc_version':r.get('calc_version'),'acquired_at':r.get('acquired_at'),'state':r.get('state'),'axes':r['axes']} for r in qgv['records'].values()],'classificationAsOf':classification['as_of'],'macro':load('macro-screen.json')['data'],'sources':[{'name':n,'asOf':load(n).get('as_of'),'sha256':hashlib.sha256((inputs/n).read_bytes()).hexdigest(),'url':'https://kco994553-star.github.io/Investment-System1/'+n} for n in ['company-classification.json','company-types-pricefree.json','news-signals.json','sec-disclosures.json','actual-catalog.json','macro-screen.json']]}
payload['sources'].insert(0,{'name':'sec-qgv2.json','asOf':qgv['as_of'],'sha256':payload['qgvSha256'],'url':'https://kco994553-star.github.io/Investment-System1/sec-qgv2.json'})
(HERE/'data.js').write_text('window.DESIGN_DATA='+json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')+';\n')
print(f'{len(rows)} company identities; {len(articles)} source records; no prices or holdings')
