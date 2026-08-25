(function(){
  'use strict';
  const anchors={
    'liam.panel.home':{module:'*',devices:['desktop','tablet','mobile'],side:'home'},
    'liam.anchor.dashboard.cuentame':{module:'dashboard',control:'dashboard.cuentame.upload',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.talent-human':{module:'dashboard',control:'dashboard.talent-human.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.nutrition':{module:'dashboard',control:'dashboard.nutrition.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.calendar':{module:'dashboard',control:'dashboard.calendar.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.document-engine':{module:'dashboard',control:'dashboard.document-engine.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.formats':{module:'dashboard',control:'dashboard.formats.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.base.upload':{module:'base-maestra',control:'base-maestra.file.upload',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.base.search':{module:'base-maestra',control:'base-maestra.units.search',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.base.process':{module:'base-maestra',control:'base-maestra.units.process',devices:['desktop','tablet'],side:'left'},
    'liam.anchor.calendar.create':{module:'calendario-inteligente',control:'calendario.activity.create',devices:['desktop','tablet'],side:'left'},
    'liam.anchor.calendar.view':{module:'calendario-inteligente',control:'calendario.view.month',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.calendar.pending':{module:'calendario-inteligente',control:'calendario.pending.list',devices:['desktop','tablet'],side:'left'},
    'liam.anchor.idp.select':{module:'motor-documental',control:'motor-documental.file.select',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.idp.upload':{module:'motor-documental',control:'motor-documental.file.upload',devices:['desktop','tablet'],side:'left'},
    'liam.anchor.idp.results':{module:'motor-documental',control:'motor-documental.document.detail',devices:['desktop','tablet'],side:'left'},
    'liam.anchor.formats.type':{module:'formatos',control:'formatos.template.type',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.formats.file':{module:'formatos',control:'formatos.template.file',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.formats.save':{module:'formatos',control:'formatos.template.save',devices:['desktop','tablet'],side:'left'}
  };
  function device(){return innerWidth<=640?'mobile':innerWidth<=1024?'tablet':'desktop'}
  function get(id){const item=Object.prototype.hasOwnProperty.call(anchors,id)?anchors[id]:null;return item&&item.devices.includes(device())?item:null}
  window.LIAM_ANCHORS=Object.freeze({get,device,ids:Object.freeze(Object.keys(anchors))});
})();
