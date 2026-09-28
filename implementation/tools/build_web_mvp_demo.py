"""Test fixture producer, OUTSIDE product runtime. Uses Track D public fixture APIs.
The cockpit receives only the resulting page/bundle, just like an operating producer.
"""
import argparse
from datetime import timedelta
from pathlib import Path
import sys
import tempfile
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[1]/'src')]
from tests.rig_fixtures import standard, T0, IDS
from investment_system.rig.network.views import NewsIndex
from investment_system.rig.intel.intel import IntelIndex
from investment_system.rig.myview.prefs import UserOrganization
from investment_system.rig.discovery.present import build_rig_page
from investment_system.rig.discovery.impact import event_impact
from investment_system.rig.discovery.discovery import fact_graph
from investment_system.product.web_mvp import repository_bundle, demo_bundle, envelope, build

class EmptyHoldings:
    def held_issuer_ids(self, as_of): return frozenset()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    b=demo_bundle(repository_bundle());s=standard();at=T0+timedelta(days=60)
    graph=s.ledger.graph_as_of(at)
    impact=event_impact(fact_graph(graph),graph,frozenset({'issuer_asml'}),'evt_r10')
    vm,page=build_rig_page(s.ledger,NewsIndex(s.lin),IntelIndex(s.ledger),EmptyHoldings(),UserOrganization(IDS),at,impacts=(impact,))
    b['news']=envelope([{'event_id':c.event_id,'headline':c.headline,'issuer_ids':list(c.issuer_ids),'available_at':c.available_at.isoformat()} for c in vm.cards],'DEMO',at.isoformat(),'tests.rig_fixtures.standard')
    b['relationships']=envelope({'frame':'network.html'},'DEMO',at.isoformat(),'Track D fixture / P0–P4')
    for n in vm.network.nodes:
        b['companies'].append({'company_id':n.issuer_id,'issuer_id':n.issuer_id,'ticker':n.label,'name':n.label,'demo':True})
    with tempfile.TemporaryDirectory() as d:
        f=Path(d)/'rig.html';f.write_text(page,encoding='utf-8');build(a.out,b,rig_page=f)
    print(a.out)

if __name__=='__main__':main()
