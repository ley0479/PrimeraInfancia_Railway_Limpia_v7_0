(function(){
  'use strict';
  const allowed=new Set(['message','progress','count','status','calendar','warning','success','next_step','module_preview','error_reference']);
  function show(payload={}){const box=document.getElementById('liam-tablet');if(!box||!allowed.has(payload.type))return false;const title=String(payload.title||'LIAM').slice(0,80);const value=String(payload.value??payload.label??'').slice(0,160);box.dataset.type=payload.type;box.querySelector('strong').textContent=title;box.querySelector('span').textContent=value;if(payload.type==='progress')box.style.setProperty('--liam-progress',`${Math.max(0,Math.min(100,Number(payload.value)||0))}%`);return true}
  window.LIAM_TABLET=Object.freeze({show,types:Object.freeze([...allowed])});
})();
