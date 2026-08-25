(function(){
  'use strict';
  const anchors={
    'liam.panel.home':{module:'*',devices:['desktop','tablet','mobile'],side:'home'},
    'liam.anchor.dashboard.cuentame':{module:'dashboard',control:'dashboard.cuentame.upload',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.talent-human':{module:'dashboard',control:'dashboard.talent-human.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.nutrition':{module:'dashboard',control:'dashboard.nutrition.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.calendar':{module:'dashboard',control:'dashboard.calendar.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.document-engine':{module:'dashboard',control:'dashboard.document-engine.open',devices:['desktop','tablet'],side:'right'},
    'liam.anchor.dashboard.formats':{module:'dashboard',control:'dashboard.formats.open',devices:['desktop','tablet'],side:'right'}
  };
  function device(){return innerWidth<=640?'mobile':innerWidth<=1024?'tablet':'desktop'}
  function get(id){const item=Object.prototype.hasOwnProperty.call(anchors,id)?anchors[id]:null;return item&&item.devices.includes(device())?item:null}
  window.LIAM_ANCHORS=Object.freeze({get,device,ids:Object.freeze(Object.keys(anchors))});
})();
