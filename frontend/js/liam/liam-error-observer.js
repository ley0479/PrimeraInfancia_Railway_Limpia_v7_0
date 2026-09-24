(function(){
  'use strict';
  if(window.__LIAM_FETCH_OBSERVER__)return;window.__LIAM_FETCH_OBSERVER__=true;
  const notified=new Set();
  function notify(payload,status){
    const incident=String(payload?.incident_id||'').trim();
    if(!incident||!payload?.diagnostic||notified.has(incident))return;
    notified.add(incident);
    document.dispatchEvent(new CustomEvent('liam:platform-error',{detail:{
      incident_id:incident,
      message:payload.error||payload.mensaje||'La operación no terminó.',
      diagnostic:payload.diagnostic,
      http_status:Number(status||0)
    }}));
  }
  const nativeFetch=window.fetch.bind(window);
  window.fetch=async function(...args){
    const response=await nativeFetch(...args);
    try{
      const url=String(args[0]?.url||args[0]||'');
      if(!response.ok&&!url.includes('/api/asistente-capacitacion/errors')){
        const type=(response.headers.get('content-type')||'').toLowerCase();
        if(type.includes('application/json')){
          const payload=await response.clone().json();
          notify(payload,response.status);
        }
      }
    }catch(_){}
    return response;
  };
  const nativeOpen=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(method,url,...rest){
    this.__liamObservedUrl=String(url||'');
    return nativeOpen.call(this,method,url,...rest);
  };
  const nativeSend=XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send=function(...args){
    if(!this.__liamObserverBound){
      this.__liamObserverBound=true;
      this.addEventListener('loadend',()=>{
        try{
          if(this.status<400||this.__liamObservedUrl.includes('/api/asistente-capacitacion/errors'))return;
          const type=String(this.getResponseHeader('content-type')||'').toLowerCase();
          if(!type.includes('application/json'))return;
          notify(JSON.parse(this.responseText||'{}'),this.status);
        }catch(_){}
      });
    }
    return nativeSend.apply(this,args);
  };
})();
