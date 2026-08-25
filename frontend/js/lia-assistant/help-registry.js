(function(){
  'use strict';
  const modules=['dashboard','buscador-beneficiarios','calendario-inteligente','administracion','panel-comercial','gerencia-general','acceso-compartido','configuracion-institucional','manual-operativo','ajustes','administrador-disenos','backups','calidad-datos','base-maestra','motor-plantillas','plantillas-oficiales','paquete-mensual','reportes-gerenciales','facturacion','formatos','nutricion','salud-nutricion','talento','cumplimiento','planeacion-pedagogica','gestion-pedagogica','gestion-coordinador','cuentas-cobro','relacion-mes','expediente-operativo-uca','biblioteca-icbf','motor-gestion-proyecto','centro-planeacion','supervision-calidad','familias-redes','componente-psicosocial','ambientes-protectores','integrity-stability','motor-documental'];
  const entries={};
  modules.forEach(module=>{
    entries[`${module}.open`]={module,description:`Abrir ${module}`,resolve(){return [...document.querySelectorAll('button,a')].find(el=>String(el.getAttribute('onclick')||el.getAttribute('href')||'').includes(module))||document.getElementById(module)}};
    entries[`${module}.screen`]={module,description:`Pantalla ${module}`,resolve(){return document.getElementById(module)}};
    entries[`${module}.primary-action`]={module,description:`Acción principal de ${module}`,resolve(){const root=document.getElementById(module);return root?.querySelector('button:not([disabled]),a[href]')||root}};
  });
  function get(helpId){return Object.prototype.hasOwnProperty.call(entries,helpId)?entries[helpId]:null}
  function primary(module){return get(`${module}.open`)}
  function resolve(helpId){return get(helpId)?.resolve()||null}
  window.LIA_HELP_REGISTRY=Object.freeze({get,primary,resolve,ids:Object.freeze(Object.keys(entries))});
})();
