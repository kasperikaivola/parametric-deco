// UI logic smoke test. A real browser render remains a separately reported check.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const viewer = fs.readFileSync('src/parametric_deco/resources/viewer.js', 'utf8');

function element(context) {
  return {checked:true,value:'0',textContent:'',children:[],append(...args){this.children.push(...args);},
    getContext(){return context;},getBoundingClientRect(){return {left:0,top:0,width:1000,height:800};},
    setPointerCapture(){}};
}

async function loadViewer(scene, fetchScene) {
  const elements = new Map(); let fills = 0, drawn = [];
  const context = {fillRect(){drawn=[];},beginPath(){},moveTo(x,y){drawn.push([x,y]);},lineTo(x,y){drawn.push([x,y]);},closePath(){},fill(){fills++;}};
  const document = {getElementById(id){if(!elements.has(id))elements.set(id,element(context));return elements.get(id);},
    createElement:()=>element(context),createTextNode:text=>({textContent:text})};
  const errors = [];
  const sandbox = {document,window:{devicePixelRatio:1,addEventListener(){},decoScene:fetchScene?undefined:scene},
    fetch:async url=>{assert.equal(url,'../scene.json');return {ok:true,json:async()=>scene};},
    console:{error:e=>errors.push(e.message)}};
  await vm.runInNewContext(viewer, sandbox);
  return {errors, elements, fills:()=>fills, drawn:()=>drawn};
}

(async()=>{
  // creature-alien-six expands to 179928 vertices. Spreading them into Math.min
  // throws "Maximum call stack size exceeded" in Qt WebEngine past ~120000.
  const count = 150000;
  const vertices = Array.from({length:count}, (_,i)=>[i, -2, 4]);
  const big = await loadViewer({
    meshes:{plate:{vertices, triangles:[[0,1,2]]}},
    instances:[{id:'plate', mesh:'plate', role:'rib',
      transform:[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]}],
    hardware_bounds:[]});
  assert.deepEqual(big.errors, []);
  assert.match(big.elements.get('status').textContent, /1 identified/);
  assert.ok(big.drawn().every(p=>p.every(Number.isFinite)), 'bounds must stay finite');

  const scene = JSON.parse(fs.readFileSync(process.argv[2] || 'build/single/scene.json', 'utf8'));
  const loaded = await loadViewer(scene, true);
  const {elements} = loaded;
  let fills = loaded.fills();
  assert.deepEqual(loaded.errors,[]); assert.match(elements.get('status').textContent,/identified/);
  assert.equal(elements.get('parts').children.length,scene.instances.length);assert.ok(fills>0);
  const before=fills;elements.get('side').onclick();fills=loaded.fills();assert.ok(fills>before);
  const assembledPixels=JSON.stringify(loaded.drawn());
  elements.get('explode').value='100';elements.get('explode').oninput();
  assert.ok(JSON.stringify(loaded.drawn())!==assembledPixels,'Explode must actually move geometry');
  elements.get('backing').checked=false;elements.get('backing').oninput();
  const first=elements.get('parts').children[0].children[0];first.checked=false;first.onchange();
  const canvas=elements.get('view');canvas.onpointerdown({clientX:100,clientY:100,pointerId:1});
  canvas.onpointermove({clientX:110,clientY:110});canvas.onpointerup({clientX:110,clientY:110});
  elements.get('front').onclick();
  console.log('Preview UI logic PASS: scene, draw, orbit, view presets, explode, visibility.');
})().catch(e=>{console.error(e);process.exitCode=1;});
