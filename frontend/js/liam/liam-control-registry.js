(function(){
  'use strict';
  const definitions={
    'dashboard.cuentame.upload':{module:'dashboard',selector:'#input-excel'},
    'dashboard.talent-human.open':{module:'dashboard',selector:'#nav-talento'},
    'dashboard.nutrition.open':{module:'dashboard',selector:'#nav-salud-nutricion'},
    'dashboard.calendar.open':{module:'dashboard',selector:'#nav-calendario-inteligente'},
    'dashboard.document-engine.open':{module:'dashboard',selector:'#nav-motor-documental'},
    'dashboard.formats.open':{module:'dashboard',selector:'#nav-formatos'},
    'dashboard.alerts.open':{module:'dashboard',selector:'#ping-alerta'},
    'base-maestra.units.select-all':{module:'base-maestra',selector:'[data-help-id="base-maestra.units.select-all"]'},
    'base-maestra.units.process':{module:'base-maestra',selector:'[data-help-id="base-maestra.units.process"]'},
    'motor-documental.file.upload':{module:'motor-documental',selector:'#idp-upload'}
  };
  function get(id){return Object.prototype.hasOwnProperty.call(definitions,id)?definitions[id]:null}
  function resolve(id){const item=get(id);return item?document.querySelector(item.selector):null}
  window.LIAM_CONTROLS=Object.freeze({get,resolve,ids:Object.freeze(Object.keys(definitions))});
})();
