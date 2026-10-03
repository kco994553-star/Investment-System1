"use strict";
const fs=require("fs"),vm=require("vm"),path=require("path"),assert=require("assert");
const root=__dirname,source="/workspace/web-g3-upstream-readonly/implementation/src/investment_system/product/web_assets/app.js";
const text=fs.readFileSync(source,"utf8"),start=text.indexOf("const SECTION_NAMES="),end=text.indexOf("function updateSettings(");
assert(start>=0&&end>start);
const context={};vm.runInNewContext(text.slice(start,end)+"\nglobalThis.actualGuard=guardSections;",context);
const base=JSON.parse(fs.readFileSync(path.join(root,"../test-vector.schema1.json"),"utf8"));
const statuses=["IDEA","PROVISIONAL","PROVISIONAL_INITIAL_PRIOR","PROVISIONAL_RESEARCH","RESEARCH"],cases=[];
for(const state of ["LIVE","FROZEN_SNAPSHOT"])for(const status of statuses)for(const location of ["section.methodology","section.producer.methodology"]){
 const b=structuredClone(base);b.qgv.state=state;
 if(location==="section.methodology")b.qgv.methodology.status=status;
 else {const m=b.qgv.methodology;delete b.qgv.methodology;m.status=status;b.qgv.producer={methodology:m};}
 const before=JSON.stringify(b),view=context.actualGuard(b);
 assert(JSON.stringify(b)===before);
 cases.push({state,status,metadata_location:location,expected_existing_policy:"WITHHOLD",actual_view_state:view.qgv.state,
   actual_data_visible:view.qgv.data!==null,original_input_unchanged:true,
   verdict:view.qgv.state==="NOT_AVAILABLE"&&view.qgv.data===null?"PASS":"FAIL_G3_BYPASS"});
}
const diagnostic=structuredClone(base);delete diagnostic.qgv.methodology;
diagnostic.qgv.producer={methodology:{id:"TEST_VECTOR_ONLY",version:"TEST_ONLY",status:"CERTIFIED_TEST_VECTOR_ONLY"}};
diagnostic.qgv.data.G3_SYNTHETIC_TEST_VECTOR_ONLY.diagnostics={old_candidate:{research_state:{status:"IDEA"}}};
const diagnosticView=context.actualGuard(diagnostic);
const receipt={upstream_head:"2b53b27fe0f570557159d02552911e9e1cc7be9c",scope:"EXISTING_UPSTREAM_FUNCTION_READ_ONLY_ORACLE",
 cases,passing:cases.filter(c=>c.verdict==="PASS").length,failing:cases.filter(c=>c.verdict!=="PASS").length,
 unrelated_nested_diagnostic:{explicit_methodology_status:"CERTIFIED_TEST_VECTOR_ONLY",diagnostic_status:"IDEA",
 actual_view_state:diagnosticView.qgv.state,actual_data_visible:diagnosticView.qgv.data!==null,
 policy_parity_question:"Existing producer validates methodology.status only; recursive diagnostic scan is broader. No publication grant is implied."},
 source_mutations_by_reviewer:0};
fs.writeFileSync(path.join(root,"adversarial-guard-oracle.json"),JSON.stringify(receipt,null,2)+"\n");
console.log(JSON.stringify({passing:receipt.passing,failing:receipt.failing,diagnostic_view_state:diagnosticView.qgv.state}));
