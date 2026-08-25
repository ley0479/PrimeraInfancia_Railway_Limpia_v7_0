(function(){
  'use strict';
  function visible(rect){return rect.width>0&&rect.height>0&&rect.bottom>0&&rect.right>0&&rect.top<innerHeight&&rect.left<innerWidth}
  function placement(targetRect,size={width:220,height:430},gap=18){
    const candidates=[
      {side:'right',left:targetRect.right+gap,top:Math.max(8,targetRect.top-size.height/3)},
      {side:'left',left:targetRect.left-size.width-gap,top:Math.max(8,targetRect.top-size.height/3)},
      {side:'bottom',left:Math.max(8,targetRect.left),top:targetRect.bottom+gap}
    ];
    const fit=candidates.find(x=>x.left>=8&&x.top>=8&&x.left+size.width<=innerWidth-8&&x.top+size.height<=innerHeight-8);
    return fit||{side:'home',left:Math.max(8,innerWidth-size.width-18),top:Math.max(8,innerHeight-size.height-18)};
  }
  window.LIAM_SAFE_ZONES=Object.freeze({visible,placement});
})();
