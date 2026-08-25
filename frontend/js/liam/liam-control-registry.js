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
    'base-maestra.file.upload':{module:'base-maestra',selector:'[data-help-id="base-maestra.file.upload"]'},
    'base-maestra.units.search':{module:'base-maestra',selector:'[data-help-id="base-maestra.units.search"]'},
    'base-maestra.units.select-all':{module:'base-maestra',selector:'[data-help-id="base-maestra.units.select-all"]'},
    'base-maestra.units.process':{module:'base-maestra',selector:'[data-help-id="base-maestra.units.process"]'},
    'calendario.activity.create':{module:'calendario-inteligente',selector:'[data-help-id="calendario.activity.create"]'},
    'calendario.schedule.upload':{module:'calendario-inteligente',selector:'[data-help-id="calendario.schedule.upload"]'},
    'calendario.view.month':{module:'calendario-inteligente',selector:'[data-help-id="calendario.view.month"]'},
    'calendario.alerts.list':{module:'calendario-inteligente',selector:'[data-help-id="calendario.alerts.list"]'},
    'calendario.pending.list':{module:'calendario-inteligente',selector:'[data-help-id="calendario.pending.list"]'},
    'motor-documental.file.select':{module:'motor-documental',selector:'[data-help-id="motor-documental.file.select"]'},
    'motor-documental.file.upload':{module:'motor-documental',selector:'[data-help-id="motor-documental.file.upload"]'},
    'motor-documental.documents.list':{module:'motor-documental',selector:'#idp-documents'},
    'motor-documental.document.detail':{module:'motor-documental',selector:'#idp-detail'},
    'formatos.template.type':{module:'formatos',selector:'[data-help-id="formatos.template.type"]'},
    'formatos.template.file':{module:'formatos',selector:'[data-help-id="formatos.template.file"]'},
    'formatos.template.save':{module:'formatos',selector:'[data-help-id="formatos.template.save"]'},
    'formatos.template.list':{module:'formatos',selector:'#plantillas-list'}
  };
  function get(id){return Object.prototype.hasOwnProperty.call(definitions,id)?definitions[id]:null}
  function resolve(id){const item=get(id);return item?document.querySelector(item.selector):null}
  window.LIAM_CONTROLS=Object.freeze({get,resolve,ids:Object.freeze(Object.keys(definitions))});
})();
