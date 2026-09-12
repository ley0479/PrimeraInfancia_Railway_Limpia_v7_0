const {test,expect}=require('@playwright/test');
test.setTimeout(90000);
test.use({launchOptions:{args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']}});

for(const device of [
  {name:'desktop',viewport:{width:900,height:700}},
  {name:'mobile',viewport:{width:390,height:844}}
]){
  test(`LIAM producción ${device.name}`,async({page})=>{
    await page.setViewportSize(device.viewport);
    const assetFailures=[];
    page.on('requestfailed',request=>{
      if(/liam-produccion-v1\.glb|model-viewer-4\.3\.1/.test(request.url()))assetFailures.push(request.url());
    });
    await page.goto('http://127.0.0.1:8765/theme-lab/liam-3d.html');
    const viewer=page.locator('#liam');
    await expect(viewer).toHaveJSProperty('loaded',true,{timeout:75000});
    const result=await viewer.evaluate(element=>({
      animations:[...element.availableAnimations],
      materials:element.model?.materials?.length||0,
      size:{width:element.getBoundingClientRect().width,height:element.getBoundingClientRect().height}
    }));
    expect(result.animations.sort()).toEqual(['Idle','Listen','Point','Talk','Think','Walk','Wave'].sort());
    expect(result.materials).toBeGreaterThanOrEqual(7);
    expect(result.size.width).toBeGreaterThan(250);
    expect(result.size.height).toBeGreaterThan(300);
    expect(assetFailures).toEqual([]);
    await viewer.screenshot({path:`test-results/liam-produccion-v1-${device.name}.png`});
  });
}
