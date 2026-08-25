(function(){
  'use strict';
  const states=new Set(['idle','greeting','listening','thinking','speaking','guiding','success','warning','error','sleeping','muted','offline']);
  let current='idle';
  function setState(next){current=states.has(next)?next:'idle';document.querySelectorAll('[data-lia-avatar]').forEach(el=>{el.dataset.state=current;el.setAttribute('aria-label',`LÍA: ${current}`)});const status=document.getElementById('lia-avatar-status');if(status)status.textContent=current}
  function getState(){return current}
  window.LIA_AVATAR=Object.freeze({setState,getState,states:Object.freeze([...states])});
})();
