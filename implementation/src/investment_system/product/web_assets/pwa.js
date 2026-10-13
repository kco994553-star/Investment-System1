/* Installation is an explicit browser gesture; credentials and app data are never cached here.
   Modes: installed (standalone) · prompt (browser offered beforeinstallprompt → explicit Install button) ·
   ios (Safari has no prompt → Share → Add to Home Screen steps) · manual (browser menu steps). */
(function(){'use strict';let prompt=null,current;
 const standalone=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;let installed=standalone();
 const ios=()=>/iPad|iPhone|iPod/.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
 function mode(){return installed?'installed':prompt?'prompt':ios()?'ios':'manual';}
 const TEXT={installed:['홈 화면에 설치됨 · 홈 화면 아이콘으로 여세요.','Installed · open it from your home screen icon.'],
  prompt:['이 브라우저는 앱 설치를 지원합니다. 아래 버튼으로 홈 화면에 추가하세요.','This browser supports installing. Use the button below to add it to your home screen.'],
  ios:['iPhone·iPad: Safari 아래쪽 공유 버튼(□↑) → "홈 화면에 추가" → "추가"를 누르세요.','iPhone/iPad: in Safari tap Share (□↑) → "Add to Home Screen" → "Add".'],
  manual:['브라우저 메뉴(⋮ 또는 ⋯) → "앱 설치" 또는 "홈 화면에 추가"를 고르세요.','Browser menu (⋮ or ⋯) → "Install app" or "Add to Home screen".']};
 function paint(){if(!current?.host.isConnected)return;const {host,en}=current,button=host.querySelector('[data-pwa-install]'),status=host.querySelector('[data-pwa-status]'),m=mode();host.setAttribute('data-pwa-mode',m);button.hidden=m!=='prompt';button.disabled=m!=='prompt';status.textContent=TEXT[m][en?1:0];}
 window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();prompt=event;paint();});window.addEventListener('appinstalled',()=>{installed=true;prompt=null;paint();});
 window.DevicePWA=Object.freeze({mode,mount(host,options={}){if(!host)return;const en=options.locale==='en-US';host.replaceChildren();const doc=host.ownerDocument,title=doc.createElement('h2'),status=doc.createElement('p'),button=doc.createElement('button'),privacy=doc.createElement('p');title.textContent=en?'Home screen app':'홈 화면 설치';status.setAttribute('data-pwa-status','');status.setAttribute('role','status');button.setAttribute('data-pwa-install','');button.type='button';button.textContent=en?'Install app (Add to Home screen)':'앱 설치 (홈 화면에 추가)';privacy.textContent=en?'Offline: static shell only. Quotes and personal data are never cached.':'오프라인에는 정적 셸만 표시합니다. 가격·개인 데이터는 캐시하지 않습니다.';privacy.className='small';host.append(title,status,button,privacy);current={host,en};button.onclick=async()=>{const pending=prompt;if(!pending||installed)return;prompt=null;paint();try{await pending.prompt();const choice=await pending.userChoice;if(choice?.outcome==='accepted')installed=true;}catch(_){}paint();};paint();}});
 if('serviceWorker' in navigator&&window.isSecureContext)navigator.serviceWorker.register('service-worker.js',{scope:'./',updateViaCache:'none'}).catch(()=>{});
})();
