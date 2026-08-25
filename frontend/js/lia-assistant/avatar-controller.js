(function(){
  'use strict';
  const states=new Set(['idle','greeting','listening','thinking','speaking','guiding','success','warning','error','sleeping','muted','offline']);
  const labels=Object.freeze({idle:'En reposo',greeting:'Saludando',listening:'Escuchando',thinking:'Pensando',speaking:'Hablando',guiding:'Guiando',success:'Proceso completado',warning:'Hay un detalle por revisar',error:'No fue posible completar la acción',sleeping:'En pausa',muted:'Audio silenciado',offline:'Ayuda sin conexión'});
  let current='idle';
  function setState(next){current=states.has(next)?next:'idle';const label=labels[current]||labels.idle;document.querySelectorAll('[data-lia-avatar]').forEach(el=>{el.dataset.state=current;el.setAttribute('aria-label',`LÍA: ${label}`);el.setAttribute('title',label)});const status=document.getElementById('lia-avatar-status');if(status)status.textContent=label}
  function getState(){return current}
  window.LIA_AVATAR=Object.freeze({setState,getState,states:Object.freeze([...states]),labels});
})();
