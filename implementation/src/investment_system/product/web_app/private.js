/* The private area (IS2.privateArea, common base 2026-10-31; FRONTEND_BRIEF §2–3, COMMON_BASE_20261031.md): one place that says
   whether private data (KIS, Lab equity curves) can be shown, and in which words. It is not built yet, so state() is
   'NOT_READY' and every screen shows 비공개 기능 준비 중.
   - state() → 'NOT_READY' today; later 'LOGIN_REQUIRED' (a private path exists, nobody signed in) or 'SIGNED_IN'.
   - text(state = state(), area) → the Korean line: NOT_READY 비공개 기능 준비 중; LOGIN_REQUIRED 로그인 필요, for area 'lab'
     비공개 연구 결과 · 로그인 필요; SIGNED_IN 비공개 영역 연결됨 (for later). An unknown state or area throws.
   No network, no storage, no session and no sign-in: nothing here pretends a login or a private request happened, and the
   LOGIN_REQUIRED / SIGNED_IN words appear only once a real private path exists (tests use them today).
   One way for every screen to add its private section (public + private two layers, owner 2026-10-31; FUNCTION_STATUS
   "공개 + 비공개 2층 구조"): PANEL_STATES and panelText(state, {area, code}) give each private panel the same states and words —
   NOT_READY 비공개 기능 준비 중 · LOGIN_REQUIRED 로그인 필요 (Lab: 비공개 연구 결과 · 로그인 필요) · LOADING 비공개 자료 불러오는 중 ·
   ERROR 비공개 자료를 불러오지 못했습니다 (+ the code) · EMPTY 비공개 자료가 아직 없습니다 · READY (the screen draws its content).
   parts.privatePanel builds the panel from these; the public part of a screen never waits for or reads a private panel. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{const I=root.IS2=root.IS2||{};I.privateArea=api.create();}})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const STATES=Object.freeze(['NOT_READY','LOGIN_REQUIRED','SIGNED_IN']);
const TEXT=Object.freeze({NOT_READY:'비공개 기능 준비 중',LOGIN_REQUIRED:'로그인 필요',SIGNED_IN:'비공개 영역 연결됨'});
const AREAS=Object.freeze({lab:Object.freeze({LOGIN_REQUIRED:'비공개 연구 결과 · 로그인 필요'})});
const PANEL_STATES=Object.freeze(['NOT_READY','LOGIN_REQUIRED','LOADING','ERROR','EMPTY','READY']);
const PANEL_TEXT=Object.freeze({LOADING:'비공개 자료 불러오는 중',ERROR:'비공개 자료를 불러오지 못했습니다',EMPTY:'비공개 자료가 아직 없습니다',READY:''});
const CODE=/^[A-Z][A-Z0-9_]{1,63}$/;
function create(){
 const state=()=>'NOT_READY';
 function text(s,area){
  const k=s===undefined?state():s;if(!STATES.includes(k))throw Error('PRIVATE_STATE_UNKNOWN');
  if(area===undefined)return TEXT[k];
  if(!Object.prototype.hasOwnProperty.call(AREAS,area))throw Error('PRIVATE_AREA_UNKNOWN');
  return Object.prototype.hasOwnProperty.call(AREAS[area],k)?AREAS[area][k]:TEXT[k];}
 // The words of one panel state; ERROR carries a fixed code (never a message, URL or value). NOT_READY / LOGIN_REQUIRED are
 // the area's words above; the first panel state is panelState() (NOT_READY today, the private path does not exist yet).
 function panelText(s,{area,code}={}){
  if(!PANEL_STATES.includes(s))throw Error('PRIVATE_PANEL_STATE_UNKNOWN');
  if(s==='NOT_READY'||s==='LOGIN_REQUIRED')return text(s,area);
  if(area!==undefined&&!Object.prototype.hasOwnProperty.call(AREAS,area))throw Error('PRIVATE_AREA_UNKNOWN');
  if(s==='ERROR'){if(code!==undefined&&!CODE.test(String(code)))throw Error('PRIVATE_CODE_INVALID');return code?PANEL_TEXT.ERROR+' · '+code:PANEL_TEXT.ERROR;}
  return PANEL_TEXT[s];}
 const panelState=()=>state()==='SIGNED_IN'?'LOADING':state();
 return Object.freeze({STATES,PANEL_STATES,state,text,panelText,panelState});
}
return Object.freeze({create,STATES,TEXT,AREAS,PANEL_STATES,PANEL_TEXT});
});
