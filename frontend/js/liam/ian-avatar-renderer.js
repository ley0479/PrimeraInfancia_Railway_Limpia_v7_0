(function(){
  'use strict';
  const genders=new Set(['male','female']);
  const variants=new Set(['afro_colombian_institutional','afro_colombian_technological','afro_colombian_educational']);
  const assets=Object.freeze({
    afro_colombian_institutional:{male:'./assets/lia/elian-afro-institutional-male-v1.png',female:'./assets/lia/liam-afro-institutional-fullbody-v2.png'},
    afro_colombian_technological:{male:'./assets/lia/elian-afro-technological-male-v1.png',female:'./assets/lia/elian-afro-technological-female-v1.png'},
    afro_colombian_educational:{male:'./assets/lia/elian-afro-educational-male-v1.png',female:'./assets/lia/elian-afro-educational-female-v1.png'}
  });
  let rigSequence=0;
  function trustedAsset(options,gender,variant){
    const requested=String(options.assetPath||'').replace(/^\//,'./');
    const allowed=new Set(['./assets/lia/lia-human-v1.png','./assets/lia/elian-afro-institutional-female-v1.png',...Object.values(assets).flatMap(Object.values)]);
    return allowed.has(requested)?requested:assets[variant][gender];
  }
  function markup(options={}){
    const gender=genders.has(options.gender)?options.gender:'female';
    const variant=variants.has(options.variant)?options.variant:'afro_colombian_institutional';
    return `<svg class="ian-avatar-svg${options.compact?' ian-avatar-compact':''}" data-gender="${gender}" data-variant="${variant}" viewBox="0 0 240 310" role="img" aria-label="Silueta animada del asistente">
      <g class="ian-body-layer"><path class="ian-shirt" d="M71 158c13-14 31-21 49-21s36 7 49 21l18 116H53z"/><path class="ian-vest" d="M72 158l33-15 15 33 15-33 33 15 10 116H62z"/><path class="ian-shirt-center" d="M106 145h28l-5 129h-18z"/><path class="ian-badge" d="M137 184h28v17h-28z"/><text x="151" y="196">LIAM</text></g>
      <g class="ian-arm ian-arm-left"><path d="M73 166c-16 13-23 37-28 65 4 7 11 9 18 5l28-55z"/><circle cx="48" cy="235" r="10"/></g><g class="ian-arm ian-arm-right"><path d="M167 166c17 13 24 37 29 65-4 7-11 9-18 5l-29-55z"/><circle cx="193" cy="235" r="10"/></g>
      <g class="ian-neck"><path d="M101 128h38v35c-12 10-26 10-38 0z"/></g><g class="ian-head-layer"><ellipse class="ian-ear" cx="76" cy="91" rx="12" ry="18"/><ellipse class="ian-ear" cx="164" cy="91" rx="12" ry="18"/><path class="ian-face" d="M76 72c2-37 22-55 44-55s42 18 44 55v36c-4 35-24 50-44 50s-40-15-44-50z"/><path class="ian-hair ian-hair-male" d="M76 76c-8-45 15-70 44-70s52 25 44 70c-8-23-21-35-44-35S84 53 76 76z"/><path class="ian-hair ian-hair-female" d="M67 84C57 34 83 4 120 4s63 30 53 80l-9 44-11-17 3-39c-8-20-20-31-36-31S92 52 84 72l3 39-11 17z"/><g class="ian-eyes"><ellipse cx="101" cy="91" rx="5" ry="4"/><ellipse cx="139" cy="91" rx="5" ry="4"/></g><path class="ian-brow" d="M92 80q9-5 18 0M130 80q9-5 18 0"/><path class="ian-nose" d="M120 92l-3 18 7 1"/><g class="ian-mouth-layer"><path class="ian-mouth-closed" d="M105 126q15 8 30 0"/><ellipse class="ian-mouth-open" cx="120" cy="128" rx="13" ry="2"/></g><path class="ian-headset" d="M75 88c0-39 21-62 45-62s45 23 45 62M164 91v26l-17 8"/><rect class="ian-headset-pad" x="64" y="83" width="13" height="26" rx="6"/></g>
      <g class="ian-tablet-layer"><rect x="82" y="203" width="76" height="58" rx="7"/><path d="M91 214h58M91 226h42M91 238h49"/></g>
    </svg>`;
  }
  function rigMarkup(options={}){
    const gender=genders.has(options.gender)?options.gender:'female';
    const variant=variants.has(options.variant)?options.variant:'afro_colombian_institutional';
    const asset=trustedAsset(options,gender,variant);
    const compact=options.compact?' ian-avatar-compact':'';
    const id=`ian-rig-${++rigSequence}`;
    return `<svg class="ian-avatar-svg ian-avatar-visual ian-avatar-rig${compact}" data-gender="${gender}" data-variant="${variant}" viewBox="0 0 1024 1536" role="img" aria-label="LIAM, asistente virtual articulada">
      <defs>
        <clipPath id="${id}-head"><path d="M285 0H735V390Q700 455 510 465Q325 450 285 385Z"/></clipPath>
        <clipPath id="${id}-left-arm"><path d="M145 385L390 380L475 585L440 980L170 995L205 690Z"/></clipPath>
        <clipPath id="${id}-right-arm"><path d="M575 385L790 380L845 700L825 985L610 970L570 610Z"/></clipPath>
        <clipPath id="${id}-left-leg"><path d="M295 690L535 690L550 1536H310Z"/></clipPath>
        <clipPath id="${id}-right-leg"><path d="M490 690L795 690L825 1536H480Z"/></clipPath>
        <mask id="${id}-body"><rect width="1024" height="1536" fill="white"/><path d="M285 0H735V390Q700 455 510 465Q325 450 285 385Z" fill="black"/><path d="M145 385L390 380L475 585L440 980L170 995L205 690Z" fill="black"/><path d="M575 385L790 380L845 700L825 985L610 970L570 610Z" fill="black"/><path d="M295 690L535 690L550 1536H310Z" fill="black"/><path d="M490 690L795 690L825 1536H480Z" fill="black"/></mask>
      </defs>
      <g class="ian-body-layer"><image href="${asset}" width="1024" height="1536" mask="url(#${id}-body)"/></g>
      <g class="ian-head-layer"><image href="${asset}" width="1024" height="1536" clip-path="url(#${id}-head)"/></g>
      <g class="ian-face-controls" aria-hidden="true"><g class="ian-eyelids"><path d="M415 218q34-18 68 0q-34 14-68 0M540 218q34-18 68 0q-34 14-68 0"/></g><g class="ian-mouth-layer"><ellipse class="ian-mouth-open" cx="511" cy="304" rx="34" ry="8"/></g></g>
      <g class="ian-arm ian-arm-left"><image href="${asset}" width="1024" height="1536" clip-path="url(#${id}-left-arm)"/></g>
      <g class="ian-arm ian-arm-right"><image href="${asset}" width="1024" height="1536" clip-path="url(#${id}-right-arm)"/></g>
      <g class="ian-leg ian-leg-left"><image href="${asset}" width="1024" height="1536" clip-path="url(#${id}-left-leg)"/></g>
      <g class="ian-leg ian-leg-right"><image href="${asset}" width="1024" height="1536" clip-path="url(#${id}-right-leg)"/></g>
    </svg>`;
  }
  function render(target,options={}){
    const el=typeof target==='string'?document.querySelector(target):target;if(!el)return null;
    const gender=genders.has(options.gender)?options.gender:'female',variant=variants.has(options.variant)?options.variant:'afro_colombian_institutional';
    el.innerHTML=rigMarkup({...options,gender,variant});
    const rig=el.querySelector('.ian-avatar-rig');
    rig?.querySelectorAll('image').forEach(image=>image.addEventListener('error',()=>{el.innerHTML=markup({gender,variant,compact:options.compact})},{once:true}));
    return rig;
  }
  window.IAN_AVATAR=Object.freeze({markup,rigMarkup,render,assets});
})();
