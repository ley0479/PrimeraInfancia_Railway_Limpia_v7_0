(function(){
  'use strict';
  if(window.__LIAM_FETCH_OBSERVER__)return;window.__LIAM_FETCH_OBSERVER__=true;
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async function(...args){
    const response=await nativeFetch(...args);
    try{
      const url=String(args[0]?.url||args[0]||'');
      if(!response.ok&&!url.includes('/api/asistente-capacitacion/errors')){
        const type=(response.headers.get('content-type')||'').toLowerCase();
        if(type.includes('application/json')){
          const payload=await response.clone().json();
          if(payload?.incident_id&&payload?.diagnostic)document.dispatchEvent(new CustomEvent('liam:platform-error',{detail:{incident_id:payload.incident_id,message:payload.error||payload.mensaje||'La operación no terminó.',diagnostic:payload.diagnostic,http_status:response.status}}));
        }
      }
    }catch(_){}
    return response;
  };
})();
