(function(){
  'use strict';
  let attempts=0,timer=null;
  const hasSession=()=>{const keys=['primeraInfanciaAuthToken','token','authToken','accessToken','primeraInfanciaToken'];for(const storage of [sessionStorage,localStorage])for(const key of keys){try{if(storage.getItem(key))return true}catch(_){}}return false};
  function removeFallback(){document.getElementById('ian-visibility-fallback')?.remove()}
  function showFallback(){
    if(document.getElementById('liam-shell')||document.getElementById('ian-visibility-fallback'))return;
    const host=document.createElement('div');host.id='ian-visibility-fallback';host.className='liam-shell ian-visibility-fallback';host.dataset.diagnostic='bootstrap-recovery';host.innerHTML='<button type="button" class="liam-tab" aria-label="Recuperar asistente IAN" title="Recuperar asistente IAN"><span class="ian-launcher-avatar"></span></button>';
    document.body.appendChild(host);window.IAN_AVATAR?.render(host.querySelector('.ian-launcher-avatar'),{compact:true});host.querySelector('button').onclick=()=>{window.IAN_BOOT?.();setTimeout(()=>{if(document.getElementById('liam-shell')){removeFallback();window.LIAM?.open?.()}},350)};
    console.warn('[IAN_DIAGNOSTIC] Se activó la silueta de recuperación porque el montaje principal no estaba presente.');
  }
  function ensure(){
    const shell=document.getElementById('liam-shell');if(shell){removeFallback();shell.style.setProperty('display','block','important');shell.style.setProperty('visibility','visible','important');shell.style.setProperty('opacity','1','important');const tab=document.getElementById('liam-tab');if(tab&&!shell.dataset.open){tab.style.setProperty('display','grid','important')}return}
    if(!hasSession()){timer=setTimeout(ensure,1400);return}
    window.IAN_BOOT?.();attempts+=1;if(attempts>=2)showFallback();timer=setTimeout(ensure,1800);
  }
  window.IAN_VISIBILITY_GUARD=Object.freeze({ensure,showFallback});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(ensure,800));else setTimeout(ensure,800);
  window.addEventListener('pagehide',()=>clearTimeout(timer));
})();
