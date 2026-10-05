"use strict";
// Display server-provided values only. No session token, local/session storage,
// financial calculation, service worker or private-data caching exists here.
const element = id => document.getElementById(id);
let csrf = null;
let connectionId = null;
let busy = false;
const engineNames = {qgv:"QGV",technical:"Technical",macro:"Macro",news:"News",chart:"ChartDocument"};
function message(value){element("message").textContent=value;}
function value(id,text){element(id).textContent=text == null ? "—" : String(text);}
function clearData(){
  connectionId=null;
  for(const id of ["total","cash","reconciliation-status"])value(id,"—");
  value("total-note","완료된 합성 데이터가 필요합니다.");
  value("connection-status","연결이 없습니다.");
  value("sync-status","완료된 동기화가 없습니다.");
  element("positions").replaceChildren();
  element("engine-status").replaceChildren();
  element("sync").disabled=true;
  element("refresh").disabled=true;
  element("connect").disabled=false;
}
async function request(method,path,body){
  const headers={};
  if(method!=="GET"){headers["Content-Type"]="application/json";if(csrf)headers["X-CSRF-Token"]=csrf;}
  const response=await fetch("/api"+path,{method,headers,credentials:"same-origin",cache:"no-store",...(body===undefined?{}:{body:JSON.stringify(body)})});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error?.code || "REQUEST_FAILED");
  return result.data;
}
async function action(fn){
  if(busy)return;
  busy=true;
  element("message").setAttribute("aria-busy","true");
  try{await fn();}catch(error){message("확인 필요: "+error.message);}
  finally{busy=false;element("message").removeAttribute("aria-busy");}
}
async function login(fixture){
  clearData();
  const data=await request("POST","/synthetic-login",{fixture_id:fixture});
  csrf=data.csrf;
  value("principal",data.principal.user_id+" · "+data.principal.tenant_id);
  value("expiry","세션 만료: "+data.expires_at);
  element("login-panel").hidden=true;
  element("dashboard").hidden=false;
  message("테스트 세션이 열렸습니다. 합성 연결을 생성하세요.");
  const connections=await request("GET","/connections");
  const existing=connections.find(item=>item.state==="ACTIVE");
  if(existing)setConnection(existing);
}
function setConnection(connection){
  connectionId=connection.id;
  value("connection-status",connection.id+" · "+(connection.state || "ACTIVE"));
  element("connect").disabled=true;element("sync").disabled=false;element("refresh").disabled=false;
}
async function renderPortfolio(){
  const data=await request("GET","/connections/"+connectionId+"/portfolio");
  if(data.data_state==="NOT_AVAILABLE"){
    message("완료된 합성 기록이 없습니다. 기록 동기화를 실행하세요.");return;
  }
  value("portfolio-status",data.portfolio_kind+" · "+data.data_state+" · 실제 계좌 아님 · "+data.as_of);
  value("total",data.analytics ? data.analytics.calculated_total+" "+data.analytics.currency : "NOT_AVAILABLE");
  value("total-note",data.analytics ? "기존 Personal Portfolio 서버 계산 결과" : "식별·완전성·통화·시간 조건을 확인해야 합니다.");
  const balances=data.balances || [];
  value("cash",balances.map(item=>item.cash+" "+item.currency).join(" / ") || "NOT_AVAILABLE");
  value("reconciliation-status",(data.reconciliation || []).map(item=>item.reported_values).join(" / ") || "NOT_COMPARABLE");
  const rows=[];
  for(const position of data.positions || []){
    const row=document.createElement("tr");
    for(const text of [position.account_id,position.security_id || "UNRESOLVED",position.quantity,position.market_value+" "+position.currency,position.resolution_status]){
      const cell=document.createElement("td");cell.textContent=text;row.append(cell);
    }
    rows.push(row);
  }
  element("positions").replaceChildren(...rows);
  const cards=[];
  for(const [name,label] of Object.entries(engineNames)){
    const state=data.engines?.[name];
    const card=document.createElement("div");card.className="dependency";
    const title=document.createElement("b");title.textContent=label;
    const detail=document.createElement("span");detail.textContent=state?.state || "NOT_AVAILABLE";
    card.append(title,detail);cards.push(card);
  }
  element("engine-status").replaceChildren(...cards);
  message("합성 기록을 표시했습니다. TARGET과 연구 엔진 출력은 연결 대기 중입니다.");
}
element("login-alice").addEventListener("click",()=>action(()=>login("fixture:alice")));
element("login-bob").addEventListener("click",()=>action(()=>login("fixture:bob")));
element("connect").addEventListener("click",()=>action(async()=>{setConnection(await request("POST","/connections",{}));message("합성 읽기 전용 연결이 생성되었습니다.");}));
element("sync").addEventListener("click",()=>action(async()=>{
  const run=await request("POST","/connections/"+connectionId+"/sync",{});
  value("sync-status",run.state+(run.error_code ? " · "+run.error_code : "")+" · "+run.id);
  await renderPortfolio();
  if(run.state!=="SUCCEEDED")message("동기화 "+run.state+" · "+(run.error_code || "일부 데이터 확인 필요")+". 마지막 완료 기록을 유지합니다.");
}));
element("refresh").addEventListener("click",()=>action(renderPortfolio));
element("logout").addEventListener("click",()=>action(async()=>{
  await request("POST","/logout",{});csrf=null;clearData();
  value("principal","—");value("expiry","");
  element("dashboard").hidden=true;element("login-panel").hidden=false;
  message("테스트 세션을 종료했습니다.");
}));
