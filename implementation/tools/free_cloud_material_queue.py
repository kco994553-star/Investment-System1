#!/usr/bin/env python3
"""Build a deterministic material-change queue for the free cloud controller.

No network and no LLM. Input is a list of changed repository paths between
previously consumed Global SHA and current Global SHA. Output is advisory state
written only into FREE_CLOUD_STATUS.json by the already-approved bounded writer.
"""

from __future__ import annotations
import argparse, json

LANES = {
    "chart": ("implementation/experiments/chart", "Chart / Portfolio / Identity / Theme"),
    "qgv": ("implementation/docs/qgv", "QGV"),
    "platform": ("implementation/docs/product", "Product Platform / Auth / Tenant / Reconciliation"),
    "web": ("implementation/web", "Web / PWA / Product API"),
    "fpia": ("implementation/docs/fpia", "FPIA / Integration / Governance"),
    "coordination": ("implementation/docs/coordination", "Main / coordination"),
}

def classify(paths:list[str])->list[dict]:
    seen=set(); out=[]
    for p in paths:
        lane=None
        if "chart" in p.lower() or "portfolio" in p.lower() or "theme" in p.lower():
            lane="chart"
        elif "qgv" in p.lower():
            lane="qgv"
        elif any(x in p.lower() for x in ["product-platform","tenant","reconciliation","financial_connector","auth"]):
            lane="platform"
        elif any(x in p.lower() for x in ["web","pwa","product_api"]):
            lane="web"
        elif any(x in p.lower() for x in ["fpia","integration","governance"]):
            lane="fpia"
        elif "coordination" in p.lower():
            lane="coordination"
        if lane and lane not in seen:
            seen.add(lane)
            out.append({
                "lane": lane,
                "label": LANES[lane][1],
                "disposition": "MAIN_REVIEW_REQUIRED",
                "reason": "material_path_changed",
            })
    return out

def build(previous_sha:str,current_sha:str,paths:list[str])->dict:
    material = previous_sha != current_sha and bool(paths)
    queue = classify(paths) if material else []
    return {
        "schema":"free-cloud-material-queue-v1",
        "previous_global_sha":previous_sha,
        "current_global_sha":current_sha,
        "material_change":material,
        "changed_paths":paths,
        "queue":queue,
        "main_action":"FRESH_READ_AND_RECONCILE" if material else "NO_ACTION",
        "automatic_product_mutation":False,
    }

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--previous-sha",required=True)
    ap.add_argument("--current-sha",required=True)
    ap.add_argument("--path",action="append",dest="paths",default=[])
    ns=ap.parse_args()
    print(json.dumps(build(ns.previous_sha,ns.current_sha,ns.paths),ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
