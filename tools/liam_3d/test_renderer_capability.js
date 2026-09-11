const fs=require('fs');
const vm=require('vm');
const source=fs.readFileSync('frontend/js/liam/liam-3d-renderer.js','utf8');

function load({reduce=false,saveData=false,memory=8,cpu=8,webgl=true}={}){
  const window={};
  const context={
    window,
    navigator:{connection:{saveData},deviceMemory:memory,hardwareConcurrency:cpu},
    matchMedia:()=>({matches:reduce}),
    document:{createElement:()=>({getContext:type=>webgl&&['webgl','webgl2'].includes(type)?{}:null})},
    customElements:{get:()=>false},Promise,Infinity
  };
  vm.runInNewContext(source,context);
  return window.LIAM_3D;
}

const cases=[
  [{},false,'disabled'],
  [{reduce:true},true,'reduced_motion'],
  [{saveData:true},true,'save_data'],
  [{memory:2},true,'low_memory'],
  [{cpu:2},true,'low_cpu'],
  [{webgl:false},true,'no_webgl'],
  [{},true,'ready']
];
for(const [options,enabled,reason] of cases){
  const result=load(options).capability(enabled);
  if(result.allowed!==(reason==='ready')||result.reason!==reason)throw new Error(`Caso ${reason} falló: ${JSON.stringify(result)}`);
}
console.log('LIAM_3D_CAPABILITY_PASS');
