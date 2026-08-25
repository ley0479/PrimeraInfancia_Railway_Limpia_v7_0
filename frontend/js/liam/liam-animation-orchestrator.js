(function(){
  'use strict';
  let cleanupTimer=null;
  function apply(state){const avatar=document.getElementById('liam-avatar');if(!avatar)return;avatar.dataset.state=state;avatar.setAttribute('aria-label',`LIAM: ${state.replaceAll('_',' ')}`);if(cleanupTimer)clearTimeout(cleanupTimer);if(['success','warning','error','greeting','teleport_in'].includes(state))cleanupTimer=setTimeout(()=>window.LIAM_STATE?.set('idle'),1600)}
  function highlight(helpId,message=''){clear();const el=window.LIAM_CONTROLS?.resolve(helpId);if(!el)return false;el.classList.add('liam-focus-target');el.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});if(message)el.setAttribute('data-liam-tip',message);return true}
  function clear(){document.querySelectorAll('.liam-focus-target').forEach(el=>{el.classList.remove('liam-focus-target');el.removeAttribute('data-liam-tip')})}
  window.LIAM_STATE?.subscribe(apply);
  window.LIAM_ANIMATION=Object.freeze({apply,highlight,clear});
})();
