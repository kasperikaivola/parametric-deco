/* Original dependency-free canvas viewer. Units are millimetres. */
'use strict';
(async function () {
  const $ = id => document.getElementById(id);
  const canvas = $('view'), ctx = canvas.getContext('2d');
  const response = await fetch('../scene.json');
  if (!response.ok) throw new Error('Cannot load generated scene.json');
  const scene = await response.json(), hidden = new Set();
  let yaw = -.4, pitch = .35, zoom = 1, triangles = [], drag = null, moved = false;
  const meshCache = new Map();
  for (const [id, mesh] of Object.entries(scene.meshes)) meshCache.set(id, mesh);
  const transform = (m,v) => [0,1,2].map(r=>m[r][0]*v[0]+m[r][1]*v[1]+m[r][2]*v[2]+m[r][3]);
  const colors = {spine:[201,149,89],rib:[224,176,113],closure:[184,128,73],armour:[201,157,102],cap:[201,157,102],blade:[219,176,113],register:[151,108,64],retainer:[151,108,64],backplate:[89,69,48],hardware:[104,120,140]};
  for (const inst of scene.instances) {
    const label=document.createElement('label'), check=document.createElement('input');
    check.type='checkbox'; check.checked=true;
    check.onchange=()=>{check.checked?hidden.delete(inst.id):hidden.add(inst.id);draw();};
    label.append(check,document.createTextNode(' '+inst.id)); $('parts').append(label);
    inst.vertices=meshCache.get(inst.mesh).vertices.map(v=>transform(inst.transform,v));
  }
  const allVertices=scene.instances.flatMap(i=>i.vertices);
  const min=[0,1,2].map(k=>Math.min(...allVertices.map(v=>v[k])));
  const max=[0,1,2].map(k=>Math.max(...allVertices.map(v=>v[k])));
  const center=min.map((v,k)=>(v+max[k])/2), span=Math.max(...max.map((v,k)=>v-min[k]),100);
  function project(v) {
    let x=v[0]-center[0], y=v[1]-center[1], z=v[2]-center[2];
    const xx=Math.cos(yaw)*x+Math.sin(yaw)*z, zz=-Math.sin(yaw)*x+Math.cos(yaw)*z;
    const yy=Math.cos(pitch)*y-Math.sin(pitch)*zz, depth=Math.sin(pitch)*y+Math.cos(pitch)*zz;
    const scale=Math.min(canvas.width,canvas.height)*.82*zoom/span;
    return [canvas.width/2+xx*scale,canvas.height/2-yy*scale,depth];
  }
  function addMesh(vertices,faces,instance,role) {
    const p=vertices.map(project);
    for (const face of faces) {
      const v=face.map(i=>p[i]);
      // Flat diffuse shading keeps individual plywood faces legible.
      const a=vertices[face[0]],b=vertices[face[1]],c=vertices[face[2]];
      const u=b.map((x,k)=>x-a[k]),w=c.map((x,k)=>x-a[k]);
      const n=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];
      const len=Math.hypot(...n)||1, shade=.5+.5*Math.abs((n[0]*.3+n[1]*.4+n[2]*.85)/len);
      triangles.push({v,depth:v.reduce((s,q)=>s+q[2],0)/3,instance,role,shade});
    }
  }
  function draw() {
    const rect=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;
    canvas.width=rect.width*dpr;canvas.height=rect.height*dpr;
    ctx.fillStyle='#12151b';ctx.fillRect(0,0,canvas.width,canvas.height);triangles=[];
    const explode=+$('explode').value;
    for (const inst of scene.instances) {
      if (hidden.has(inst.id)||inst.role==='backplate'&&!$('backing').checked) continue;
      let shift=[0,0,0];
      if(['rib','armour'].includes(inst.role)) shift=[0,0,explode];
      if(['closure','cap','blade','retainer'].includes(inst.role)) shift=[0,0,explode*2];
      if(inst.role==='spine') shift=[0,Math.sign(inst.vertices[0][1]-center[1])*explode*.25,0];
      addMesh(inst.vertices.map(v=>v.map((n,k)=>n+shift[k])),meshCache.get(inst.mesh).triangles,inst,inst.role);
    }
    if($('hardware').checked) for (const [index,b] of scene.hardware_bounds.entries()) {
      const lo=b.slice(1,4),hi=b.slice(4,7),verts=[];
      if(b[0].endsWith('-clip')) {lo[2]+=explode*2;hi[2]+=explode*2;}
      for(let i=0;i<8;i++) verts.push([i&1?hi[0]:lo[0],i&2?hi[1]:lo[1],i&4?hi[2]:lo[2]]);
      addMesh(verts,[[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]],
              {id:'hardware-envelope-'+index,mesh:'illustrative conservative hardware envelope'},'hardware');
    }
    triangles.sort((a,b)=>a.depth-b.depth);
    for(const t of triangles) {
      ctx.beginPath();ctx.moveTo(t.v[0][0],t.v[0][1]);ctx.lineTo(t.v[1][0],t.v[1][1]);ctx.lineTo(t.v[2][0],t.v[2][1]);ctx.closePath();
      ctx.fillStyle=`rgb(${(colors[t.role]||colors.rib).map(c=>Math.round(c*t.shade)).join(',')})`;ctx.fill();
    }
  }
  canvas.onpointerdown=e=>{drag=[e.clientX,e.clientY];moved=false;canvas.setPointerCapture(e.pointerId);};
  canvas.onpointermove=e=>{if(!drag)return;const dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(Math.abs(dx)+Math.abs(dy)>1)moved=true;yaw+=dx*.008;pitch=Math.max(-1.5,Math.min(1.5,pitch+dy*.008));drag=[e.clientX,e.clientY];draw();};
  canvas.onpointerup=e=>{
    drag=null;if(moved)return;
    const r=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1,p=[(e.clientX-r.left)*dpr,(e.clientY-r.top)*dpr];
    for(const t of [...triangles].reverse()) {
      const signs=t.v.map((a,i)=>{const b=t.v[(i+1)%3];return(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]);});
      if(signs.every(x=>x>=0)||signs.every(x=>x<=0)) {$('pick').textContent=t.instance.id+' · '+t.instance.mesh;break;}
    }
  };
  canvas.onwheel=e=>{e.preventDefault();zoom=Math.max(.2,Math.min(5,zoom*Math.exp(-e.deltaY*.001)));draw();};
  $('front').onclick=()=>{yaw=0;pitch=0;draw();};$('side').onclick=()=>{yaw=Math.PI/2;pitch=0;draw();};
  $('orbit').onclick=()=>{yaw=-.4;pitch=.35;draw();};
  for(const id of ['explode','backing','hardware'])$(id).oninput=draw;
  window.addEventListener('resize',draw);
  $('status').textContent=scene.instances.length+' identified plywood instances · orbit preview';
  draw();
})().catch(error=>{document.getElementById('status').textContent=error.message;console.error(error);});
