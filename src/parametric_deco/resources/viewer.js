/* Dependency-free orbit preview. Units are millimetres.
   WebGL keeps one baked mesh and only updates camera uniforms while orbiting.
   The canvas path remains for engines without WebGL, including the node smoke test. */
'use strict';
(async function () {
  const $ = id => document.getElementById(id);
  const canvas = $('view');
  let scene = window.decoScene;
  if (!scene) {
    const response = await fetch('../scene.json');
    if (!response.ok) throw new Error('Cannot load generated scene.json');
    scene = await response.json();
  }
  const hidden = new Set();
  let yaw = -.4, pitch = .35, zoom = 1, drag = null, moved = false, drawing = false;
  const meshCache = new Map();
  for (const [id, mesh] of Object.entries(scene.meshes)) meshCache.set(id, mesh);
  const transform = (m, v) => [0, 1, 2].map(r => m[r][0] * v[0] + m[r][1] * v[1] + m[r][2] * v[2] + m[r][3]);
  const colors = {spine:[201,149,89], rib:[224,176,113], closure:[184,128,73], armour:[201,157,102],
    cap:[201,157,102], blade:[219,176,113], register:[151,108,64], retainer:[151,108,64],
    backplate:[89,69,48], hardware:[104,120,140]};
  const boxFaces = [[0,1,3],[0,3,2],[4,6,7],[4,7,5],[0,4,5],[0,5,1],[2,3,7],[2,7,6],[0,2,6],[0,6,4],[1,5,7],[1,7,3]];
  for (const inst of scene.instances) {
    const label = document.createElement('label'), check = document.createElement('input');
    check.type = 'checkbox'; check.checked = true;
    check.onchange = () => { check.checked ? hidden.delete(inst.id) : hidden.add(inst.id); draw(); };
    label.append(check, document.createTextNode(' ' + inst.id)); $('parts').append(label);
    inst.vertices = meshCache.get(inst.mesh).vertices.map(v => transform(inst.transform, v));
  }
  const allVertices = scene.instances.flatMap(i => i.vertices);
  // A spread into Math.min overflows the JS stack past ~125k vertices.
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (const v of allVertices) for (let k = 0; k < 3; k++) {
    if (v[k] < min[k]) min[k] = v[k];
    if (v[k] > max[k]) max[k] = v[k];
  }
  const center = min.map((v, k) => (v + max[k]) / 2);
  const span = Math.max(max[0] - min[0], max[1] - min[1], max[2] - min[2], 100);

  function shadeOf(a, b, c) {
    const ux = b[0] - a[0], uy = b[1] - a[1], uz = b[2] - a[2];
    const wx = c[0] - a[0], wy = c[1] - a[1], wz = c[2] - a[2];
    const nx = uy * wz - uz * wy, ny = uz * wx - ux * wz, nz = ux * wy - uy * wx;
    const len = Math.hypot(nx, ny, nz) || 1;
    return .5 + .5 * Math.abs((nx * .3 + ny * .4 + nz * .85) / len);
  }
  function shiftFor(role, inst) {
    if (role === 'spine') return [0, Math.sign(inst.vertices[0][1] - center[1]) * .25, 0];
    if (role === 'rib' || role === 'armour') return [0, 0, 1];
    if (role === 'closure' || role === 'cap' || role === 'blade' || role === 'retainer') return [0, 0, 2];
    return [0, 0, 0];
  }
  function obtainGL() {
    // Antialiasing a full assembly is fill-rate the orbit does not need.
    const optionSets = [
      {alpha: false, antialias: false, depth: true, stencil: false,
        powerPreference: 'high-performance'},
      {alpha: false, antialias: false, depth: true, stencil: false},
    ];
    for (const attrs of optionSets) {
      for (const name of ['webgl2', 'webgl']) {
        try {
          const gl = canvas.getContext(name, attrs);
          if (gl && typeof gl.createShader === 'function') return gl;
        } catch (error) { /* The node smoke test has no WebGL. */ }
      }
    }
    return null;
  }
  const gl = obtainGL();
  const ctx = gl ? null : canvas.getContext('2d');

  let program = null, meshBuffer = null, fullData = null, ranges = [], pickList = [null];
  let uploadedKey = '', uploadedCount = 0, fullKey = '';
  let pickTarget = null, pickColor = null, pickDepth = null, pickW = 0, pickH = 0;
  const loc = {};

  function compile(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
      throw new Error(gl.getShaderInfoLog(shader) || 'shader compile failed');
    return shader;
  }
  function initGL() {
    const vs = compile(gl.VERTEX_SHADER, `
      attribute vec3 aPos;
      attribute vec3 aColor;
      attribute vec3 aShift;
      attribute float aId;
      uniform float uYaw, uPitch, uScaleX, uScaleY, uDepth, uExplode;
      varying vec3 vColor;
      varying float vId;
      void main() {
        vec3 p = aPos + aShift * uExplode;
        float cy = cos(uYaw), sy = sin(uYaw), cp = cos(uPitch), sp = sin(uPitch);
        float xx = cy * p.x + sy * p.z;
        float zz = -sy * p.x + cy * p.z;
        float yy = cp * p.y - sp * zz;
        float depth = sp * p.y + cp * zz;
        gl_Position = vec4(xx * uScaleX, yy * uScaleY, -depth * uDepth, 1.0);
        vColor = aColor;
        vId = aId;
      }`);
    const fs = compile(gl.FRAGMENT_SHADER, `
      precision highp float;
      varying vec3 vColor;
      varying float vId;
      uniform float uPick;
      void main() {
        if (uPick > 0.5) {
          float id = vId;
          float r = mod(id, 256.0);
          float g = mod(floor(id / 256.0), 256.0);
          float b = floor(id / 65536.0);
          gl_FragColor = vec4(r / 255.0, g / 255.0, b / 255.0, 1.0);
        } else {
          gl_FragColor = vec4(vColor, 1.0);
        }
      }`);
    program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS))
      throw new Error(gl.getProgramInfoLog(program) || 'shader link failed');
    for (const name of ['uYaw', 'uPitch', 'uScaleX', 'uScaleY', 'uDepth', 'uExplode', 'uPick'])
      loc[name] = gl.getUniformLocation(program, name);
    loc.pos = gl.getAttribLocation(program, 'aPos');
    loc.color = gl.getAttribLocation(program, 'aColor');
    loc.shift = gl.getAttribLocation(program, 'aShift');
    loc.id = gl.getAttribLocation(program, 'aId');
    let corners = scene.hardware_bounds.length * boxFaces.length * 3;
    for (const inst of scene.instances)
      corners += meshCache.get(inst.mesh).triangles.length * 3;
    const data = new Float32Array(corners * 10);
    let cursor = 0;
    function writeFace(verts, face, shift, rgb, id) {
      const tri = face.map(i => verts[i]);
      const shade = shadeOf(tri[0], tri[1], tri[2]);
      for (const v of tri) {
        data[cursor++] = v[0] - center[0];
        data[cursor++] = v[1] - center[1];
        data[cursor++] = v[2] - center[2];
        data[cursor++] = rgb[0] * shade / 255;
        data[cursor++] = rgb[1] * shade / 255;
        data[cursor++] = rgb[2] * shade / 255;
        data[cursor++] = shift[0];
        data[cursor++] = shift[1];
        data[cursor++] = shift[2];
        data[cursor++] = id;
      }
    }
    function addRange(verts, faces, shift, role, meta) {
      const id = pickList.length;
      pickList.push(meta);
      const first = cursor / 10;
      const rgb = colors[role] || colors.rib;
      for (const face of faces) writeFace(verts, face, shift, rgb, id);
      ranges.push({first, count: cursor / 10 - first, hardware: role === 'hardware',
        backplate: role === 'backplate', instanceId: meta.id});
    }
    for (const inst of scene.instances)
      addRange(inst.vertices, meshCache.get(inst.mesh).triangles, shiftFor(inst.role, inst),
        inst.role, {id: inst.id, mesh: inst.mesh});
    scene.hardware_bounds.forEach((b, index) => {
      const lo = b.slice(1, 4), hi = b.slice(4, 7), verts = [];
      for (let i = 0; i < 8; i++)
        verts.push([i & 1 ? hi[0] : lo[0], i & 2 ? hi[1] : lo[1], i & 4 ? hi[2] : lo[2]]);
      addRange(verts, boxFaces, b[0].endsWith('-clip') ? [0, 0, 2] : [0, 0, 0], 'hardware',
        {id: 'hardware-envelope-' + index, mesh: 'illustrative conservative hardware envelope'});
    });
    fullData = data;
    meshBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, meshBuffer);
    const stride = 40;
    gl.bufferData(gl.ARRAY_BUFFER, fullData, gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(loc.pos);
    gl.vertexAttribPointer(loc.pos, 3, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(loc.color);
    gl.vertexAttribPointer(loc.color, 3, gl.FLOAT, false, stride, 12);
    gl.enableVertexAttribArray(loc.shift);
    gl.vertexAttribPointer(loc.shift, 3, gl.FLOAT, false, stride, 24);
    gl.enableVertexAttribArray(loc.id);
    gl.vertexAttribPointer(loc.id, 1, gl.FLOAT, false, stride, 36);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);
    uploadedCount = fullData.length / 10;
    fullKey = visibleKey();
    uploadedKey = fullKey;
    pickTarget = gl.createFramebuffer();
  }
  function visibleKey() {
    let key = ($('backing').checked ? 'b' : '') + ($('hardware').checked ? 'h' : '') + ':';
    for (const id of hidden) key += id + '\n';
    return key;
  }
  function shown(range) {
    if (range.hardware) return $('hardware').checked;
    if (range.backplate && !$('backing').checked) return false;
    return !hidden.has(range.instanceId);
  }
  function bindVisible() {
    const key = visibleKey();
    if (key === uploadedKey) return;
    let data = fullData;
    if (key !== fullKey) {
      let count = 0;
      for (const range of ranges) if (shown(range)) count += range.count;
      data = new Float32Array(count * 10);
      let offset = 0;
      for (const range of ranges) if (shown(range)) {
        const start = range.first * 10, end = (range.first + range.count) * 10;
        data.set(fullData.subarray(start, end), offset);
        offset += end - start;
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, meshBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);
    uploadedCount = data.length / 10;
    uploadedKey = key;
  }
  function cameraUniforms(pick) {
    const w = canvas.width, h = canvas.height;
    const pixel = Math.min(w, h) * .82 * zoom / span;
    gl.uniform1f(loc.uYaw, yaw);
    gl.uniform1f(loc.uPitch, pitch);
    gl.uniform1f(loc.uScaleX, pixel * 2 / w);
    gl.uniform1f(loc.uScaleY, pixel * 2 / h);
    // Explode shifts at most 360 mm. Keep that, plus the assembly, inside clip space.
    gl.uniform1f(loc.uDepth, .9 / (span * .9 + 360));
    gl.uniform1f(loc.uExplode, +$('explode').value || 0);
    gl.uniform1f(loc.uPick, pick ? 1 : 0);
  }
  function ensurePickTarget() {
    const w = canvas.width, h = canvas.height;
    if (pickColor && pickW === w && pickH === h) return;
    pickW = w; pickH = h;
    gl.bindFramebuffer(gl.FRAMEBUFFER, pickTarget);
    if (pickColor) {
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, null, 0);
      gl.deleteTexture(pickColor);
    }
    if (pickDepth) {
      gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, null);
      gl.deleteRenderbuffer(pickDepth);
    }
    // Default min-filter wants mipmaps, which would make this target incomplete.
    pickColor = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, pickColor);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    pickDepth = gl.createRenderbuffer();
    gl.bindRenderbuffer(gl.RENDERBUFFER, pickDepth);
    gl.renderbufferStorage(gl.RENDERBUFFER, gl.DEPTH_COMPONENT16, w, h);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, pickColor, 0);
    gl.framebufferRenderbuffer(gl.FRAMEBUFFER, gl.DEPTH_ATTACHMENT, gl.RENDERBUFFER, pickDepth);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  function paintGL() {
    if (!program) initGL();
    bindVisible();
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(18 / 255, 21 / 255, 27 / 255, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(program);
    cameraUniforms(false);
    if (uploadedCount) gl.drawArrays(gl.TRIANGLES, 0, uploadedCount);
  }
  function pickGL(px, py) {
    if (!program) return;
    ensurePickTarget();
    bindVisible();
    gl.bindFramebuffer(gl.FRAMEBUFFER, pickTarget);
    if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      return;
    }
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0, 0, 0, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(program);
    cameraUniforms(true);
    if (uploadedCount) gl.drawArrays(gl.TRIANGLES, 0, uploadedCount);
    const pixel = new Uint8Array(4);
    const x = Math.max(0, Math.min(canvas.width - 1, Math.floor(px)));
    const y = Math.max(0, Math.min(canvas.height - 1, Math.floor(canvas.height - py)));
    gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    const id = pixel[0] + pixel[1] * 256 + pixel[2] * 65536;
    const hit = pickList[id];
    if (hit) $('pick').textContent = hit.id + ' · ' + hit.mesh;
  }

  function project(v) {
    const x = v[0] - center[0], y = v[1] - center[1], z = v[2] - center[2];
    const xx = Math.cos(yaw) * x + Math.sin(yaw) * z, zz = -Math.sin(yaw) * x + Math.cos(yaw) * z;
    const yy = Math.cos(pitch) * y - Math.sin(pitch) * zz, depth = Math.sin(pitch) * y + Math.cos(pitch) * zz;
    const scale = Math.min(canvas.width, canvas.height) * .82 * zoom / span;
    return [canvas.width / 2 + xx * scale, canvas.height / 2 - yy * scale, depth];
  }
  let triangles = [];
  function addMesh(vertices, faces, instance, role) {
    const p = vertices.map(project);
    for (const face of faces) {
      const tri = face.map(i => vertices[i]);
      triangles.push({v: face.map(i => p[i]), depth: face.reduce((s, i) => s + p[i][2], 0) / 3,
        instance, role, shade: shadeOf(tri[0], tri[1], tri[2])});
    }
  }
  function paint2D() {
    ctx.fillStyle = '#12151b';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    triangles = [];
    const explode = +$('explode').value;
    for (const inst of scene.instances) {
      if (hidden.has(inst.id) || inst.role === 'backplate' && !$('backing').checked) continue;
      const shift = shiftFor(inst.role, inst).map(n => n * explode);
      addMesh(inst.vertices.map(v => v.map((n, k) => n + shift[k])),
        meshCache.get(inst.mesh).triangles, inst, inst.role);
    }
    if ($('hardware').checked) scene.hardware_bounds.forEach((b, index) => {
      const lo = b.slice(1, 4), hi = b.slice(4, 7), verts = [];
      const extra = b[0].endsWith('-clip') ? explode * 2 : 0;
      for (let i = 0; i < 8; i++)
        verts.push([i & 1 ? hi[0] : lo[0], i & 2 ? hi[1] : lo[1], i & 4 ? hi[2] : lo[2] + extra]);
      addMesh(verts, boxFaces,
        {id: 'hardware-envelope-' + index, mesh: 'illustrative conservative hardware envelope'},
        'hardware');
    });
    triangles.sort((a, b) => a.depth - b.depth);
    for (const t of triangles) {
      ctx.beginPath();
      ctx.moveTo(t.v[0][0], t.v[0][1]);
      ctx.lineTo(t.v[1][0], t.v[1][1]);
      ctx.lineTo(t.v[2][0], t.v[2][1]);
      ctx.closePath();
      ctx.fillStyle = `rgb(${(colors[t.role] || colors.rib).map(c => Math.round(c * t.shade)).join(',')})`;
      ctx.fill();
    }
  }
  function resizeCanvas() {
    const rect = canvas.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.round(rect.width * dpr)), h = Math.max(1, Math.round(rect.height * dpr));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
  }
  let layoutWaits = 0;
  function draw() {
    if (drawing) return;
    drawing = true;
    try {
      resizeCanvas();
      if (canvas.width < 2 || canvas.height < 2) {
        if (layoutWaits < 120 && typeof window.requestAnimationFrame === 'function') {
          layoutWaits += 1;
          window.requestAnimationFrame(draw);
        }
        return;
      }
      layoutWaits = 0;
      if (gl) paintGL();
      else paint2D();
    } finally {
      drawing = false;
    }
  }
  let scheduled = 0;
  function requestDraw() {
    if (typeof window.requestAnimationFrame !== 'function') { draw(); return; }
    if (scheduled) return;
    scheduled = window.requestAnimationFrame(() => { scheduled = 0; draw(); });
  }
  canvas.onpointerdown = e => {
    drag = [e.clientX, e.clientY];
    moved = false;
    try { canvas.setPointerCapture(e.pointerId); } catch (error) { /* Pointer already released. */ }
  };
  canvas.onpointermove = e => {
    if (!drag) return;
    const dx = e.clientX - drag[0], dy = e.clientY - drag[1];
    if (Math.abs(dx) + Math.abs(dy) > 1) moved = true;
    yaw += dx * .008;
    pitch = Math.max(-1.5, Math.min(1.5, pitch + dy * .008));
    drag = [e.clientX, e.clientY];
    if (gl) requestDraw(); else draw();
  };
  canvas.onpointerup = e => {
    drag = null;
    if (moved) return;
    const rect = canvas.getBoundingClientRect();
    const px = (e.clientX - rect.left) * canvas.width / rect.width;
    const py = (e.clientY - rect.top) * canvas.height / rect.height;
    if (gl) pickGL(px, py);
    else {
      for (const t of [...triangles].reverse()) {
        const signs = t.v.map((a, i) => {
          const b = t.v[(i + 1) % 3];
          return (b[0] - a[0]) * (py - a[1]) - (b[1] - a[1]) * (px - a[0]);
        });
        if (signs.every(x => x >= 0) || signs.every(x => x <= 0)) {
          $('pick').textContent = t.instance.id + ' · ' + t.instance.mesh;
          break;
        }
      }
    }
  };
  canvas.onwheel = e => {
    e.preventDefault();
    zoom = Math.max(.2, Math.min(5, zoom * Math.exp(-e.deltaY * .001)));
    if (gl) requestDraw(); else draw();
  };
  $('front').onclick = () => { yaw = 0; pitch = 0; draw(); };
  $('side').onclick = () => { yaw = Math.PI / 2; pitch = 0; draw(); };
  $('orbit').onclick = () => { yaw = -.4; pitch = .35; draw(); };
  for (const id of ['explode', 'backing', 'hardware']) $(id).oninput = draw;
  window.addEventListener('resize', draw);
  window.decoGetView = () => ({yaw, pitch, zoom, explode: $('explode').value,
    backing: $('backing').checked, hardware: $('hardware').checked});
  window.decoSetView = view => {
    if (!view || ![view.yaw, view.pitch, view.zoom].every(Number.isFinite)) return;
    yaw = view.yaw; pitch = view.pitch; zoom = Math.max(.2, Math.min(5, view.zoom));
    $('explode').value = view.explode || 0;
    $('backing').checked = view.backing !== false;
    $('hardware').checked = view.hardware !== false;
    draw();
  };
  $('status').textContent = scene.instances.length + ' identified plywood instances · orbit preview';
  draw();
})().catch(error => {
  const status = document.getElementById('status');
  if (status) status.textContent = error.message;
  console.error(error);
});
