/* New frontend core (docs/frontend_v2/FRONTEND_V2_PLAN.md): DOM builder, menu table, hash router, screen registry.
   Classic script with one global (IS2) so it runs under the same CSP ('self') and loads in node tests via require().
   No innerHTML for data: every text goes through text nodes. Nothing here stores or sends anything. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.IS2=Object.assign(root.IS2||{},api);})(typeof globalThis==='object'?globalThis:this,function(){
'use strict';
const SVG='http://www.w3.org/2000/svg';
/* h('div',{class:'x',onclick:fn,'aria-label':'..'},child,...) - children: Node, string, number, array, null/false (skipped).
   Never a script element, in either namespace (TAG_INVALID): scripts come from loader.js LOAD_ORDER only (P2-1a), so a screen
   cannot add one the CSP ('self') would run outside that list. The SVG part takes a plain local name only: createElementNS also
   accepts a qualified name ('x:script' makes an SVG <script>), so any further ':' is refused too. */
const SCRIPT_TAG=/^\s*(?:svg:)?script\s*$/i;
function h(tag,attrs,...children){
 if(typeof tag!=='string'||SCRIPT_TAG.test(tag)||/^svg:.*:/i.test(tag)||/^(?!svg:).*:/i.test(tag)||/^\s*svg:\s*$/i.test(tag))throw Error('TAG_INVALID');
 const svg=tag.startsWith('svg:'),el=svg?document.createElementNS(SVG,tag.slice(4)):document.createElement(tag);
 for(const[k,v]of Object.entries(attrs||{})){
  if(v===null||v===undefined||v===false)continue;
  if(k.startsWith('on')&&typeof v==='function')el.addEventListener(k.slice(2),v);
  else if(k==='dataset')Object.assign(el.dataset,v);
  // CSSOM only (CSP has no 'unsafe-inline'): {style:{width:'40%'}} sets properties, never a style attribute string (the CSP
  // would drop it silently, so a string is refused here instead).
  else if(k==='style'){if(typeof v!=='object')throw Error('STYLE_INVALID');for(const[p,x]of Object.entries(v))el.style.setProperty(p,String(x));}
  else el.setAttribute(k,v===true?'':String(v));
 }
 append(el,children);return el;
}
function append(el,children){for(const c of children.flat(Infinity)){if(c===null||c===undefined||c===false)continue;el.appendChild(c instanceof Node?c:document.createTextNode(String(c)));}return el;}
// Inline stroke icons (draft style): a list of SVG path data strings on a viewBox square.
function icon(paths,size=36,label=null){
 const s=h('svg:svg',{class:'ico',width:size,height:size,viewBox:'0 0 '+size+' '+size,...(label?{role:'img','aria-label':label}:{'aria-hidden':'true'})});
 for(const d of paths)s.appendChild(h('svg:path',{d}));return s;}

/* Menu numbers follow the draft (0 = 기업 검색 ... n+1 = Lab); route ids are stable hash paths. */
const MENU=Object.freeze([
 {id:'search',no:'0',ko:'기업 검색',path:'/'},
 {id:'qgv',no:'1',ko:'QGV',path:'/qgv'},
 {id:'technical',no:'2',ko:'기술적 분석',path:'/technical'},
 {id:'macro',no:'3',ko:'매크로',path:'/macro'},
 {id:'news',no:'4',ko:'뉴스',path:'/news'},
 {id:'portfolio',no:'5',ko:'포트폴리오',path:'/portfolio'},
 {id:'prompts',no:'6',ko:'프롬프트',path:'/prompts'},
 {id:'tree',no:'n',ko:'구조 트리',path:'/tree'},
 {id:'lab',no:'n+1',ko:'Lab',path:'/lab'},
].map(Object.freeze));
// Phone bottom tabs (draft note: 홈 · QGV · 포트폴리오 · 뉴스 · 전체 메뉴).
const TABS=Object.freeze(['search','qgv','portfolio','news']);
/* Detail screens: features without a place on the draft's first screens (owner decision 2026-10-23: moved, not deleted). */
const DETAILS=Object.freeze([
 {id:'settings',ko:'설정 · 구글 시트 연결'},
 {id:'data-status',ko:'자료 상태 · 새로고침'},
 {id:'financials',ko:'재무 상세'},
 {id:'sec-cover',ko:'SEC 표지 정보'},
 {id:'playbook',ko:'플레이북 기록'},
 {id:'virtual-trading',ko:'가상매매'},
 {id:'target-v1',ko:'TARGET v1 빌더'},
].map(Object.freeze));

/* '#/company/NYSE%3AFIX' -> {id:'company', params:['NYSE:FIX']}; unknown -> search. */
function parse(hash){
 const raw=String(hash||'').replace(/^#/,'');const parts=raw.split('/').filter(Boolean).map(p=>{try{return decodeURIComponent(p);}catch(_){return p;}});
 if(!parts.length)return{id:'search',params:[]};
 const [head,...rest]=parts;
 if(head==='company'&&rest.length)return{id:'company',params:rest.slice(0,1)};
 if(head==='detail'&&rest.length&&DETAILS.some(d=>d.id===rest[0]))return{id:'detail',params:rest.slice(0,1)};
 const m=MENU.find(x=>x.id===head&&x.id!=='search');
 return m?{id:m.id,params:rest}:{id:'search',params:[]};
}
function href(id,...params){if(id==='search')return'#/';return'#/'+[id,...params].map(encodeURIComponent).join('/');}
// The menu entry a route belongs to (company results sit under 0. 기업 검색, details under none).
function menuOf(route){return route.id==='company'?'search':MENU.some(m=>m.id===route.id)?route.id:null;}

/* Screen registry. Lane files load before the P0 placeholder screens (index.html), so a placeholder never replaces a real
   screen, a real screen replaces a placeholder, and a second real screen for one route is a lane conflict (SCREEN_DUPLICATE)
   instead of a silent overwrite. Detail screens (#/detail/<id>) register by name the same way. */
const screens=new Map(),details=new Map();
function put(map,id,render,placeholder){
 if(typeof render!=='function')throw Error('SCREEN_INVALID');
 const had=map.get(id);
 if(had&&!had.placeholder){if(placeholder)return;throw Error('SCREEN_DUPLICATE');}
 map.set(id,{render,placeholder});
}
function register(id,render,opts){put(screens,id,render,!!(opts&&opts.placeholder===true));}
function registerDetail(name,render){if(!DETAILS.some(d=>d.id===name))throw Error('DETAIL_UNKNOWN');put(details,name,render,false);}
function screen(id){const s=screens.get(id);return s?s.render:null;}
function detail(name){const s=details.get(name);return s?s.render:null;}
function isPlaceholder(id){const s=screens.get(id);return !!(s&&s.placeholder);}

/* The selected company (feature 1.1.2 "화면을 이동해도 선택 기업을 유지"): RAM only, set by the company page once its id resolves
   (a TARGET company_id or a Universe code), kept across menus until the page is reloaded. Nothing is stored or sent. */
let chosen=null;const watchers=new Set();
const selection=Object.freeze({
 get:()=>chosen===null?null:Object.freeze({id:chosen}),
 set(id){const next=typeof id==='string'&&id?id:null;if(next===chosen)return;chosen=next;const v=selection.get();for(const fn of[...watchers]){try{fn(v);}catch(_){}}},
 subscribe(fn,{signal}={}){if(typeof fn!=='function')throw Error('SUBSCRIBER_INVALID');if(signal&&signal.aborted)return()=>{};watchers.add(fn);
  const off=()=>{watchers.delete(fn);};if(signal)signal.addEventListener('abort',off,{once:true});return off;}});

return Object.freeze({h,append,icon,MENU,TABS,DETAILS,parse,href,menuOf,register,registerDetail,screen,detail,isPlaceholder,selection});
});
