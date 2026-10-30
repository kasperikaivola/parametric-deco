// UI logic smoke test. A real browser render remains a separately reported check.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const scene = JSON.parse(fs.readFileSync(process.argv[2] || 'build/single/scene.json', 'utf8'));
const elements = new Map(); let fills = 0, drawn = [];
const context = {fillRect(){drawn=[];},beginPath(){},moveTo(x,y){drawn.push([x,y]);},lineTo(x,y){drawn.push([x,y]);},closePath(){},fill(){fills++;}};
function element(id) {
  return {id,checked:true,value:'0',textContent:'',children:[],append(...args){this.children.push(...args);},
    getContext(){return context;},getBoundingClientRect(){return {left:0,top:0,width:1000,height:800};},
    setPointerCapture(){}};
}
const document = {getElementById(id){if(!elements.has(id))elements.set(id,element(id));return elements.get(id);},
  createElement:tag=>element(tag),createTextNode:text=>({textContent:text})};
const errors = [];
const sandbox = {document,window:{devicePixelRatio:1,addEventListener(){}},
  fetch:async url=>{assert.equal(url,'../scene.json');return {ok:true,json:async()=>scene};},
  console:{error:e=>errors.push(e.message)}};
(async()=>{
  await vm.runInNewContext(fs.readFileSync('src/parametric_deco/resources/viewer.js','utf8'),sandbox);
  assert.deepEqual(errors,[]); assert.match(elements.get('status').textContent,/identified/);
  assert.equal(elements.get('parts').children.length,scene.instances.length);assert.ok(fills>0);
  const before=fills;elements.get('side').onclick();assert.ok(fills>before);
  const assembledPixels=JSON.stringify(drawn);
  elements.get('explode').value='100';elements.get('explode').oninput();
  assert.ok(JSON.stringify(drawn)!==assembledPixels,'Explode must actually move geometry');
  elements.get('backing').checked=false;elements.get('backing').oninput();
  const first=elements.get('parts').children[0].children[0];first.checked=false;first.onchange();
  const canvas=elements.get('view');canvas.onpointerdown({clientX:100,clientY:100,pointerId:1});
  canvas.onpointermove({clientX:110,clientY:110});canvas.onpointerup({clientX:110,clientY:110});
  elements.get('front').onclick();
  console.log('Preview UI logic PASS: scene, draw, orbit, view presets, explode, visibility. Real browser NOT RUN.');
})().catch(e=>{console.error(e);process.exitCode=1;});
