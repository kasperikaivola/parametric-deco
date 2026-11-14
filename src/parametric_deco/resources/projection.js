/* Surface-atlas renderer. Buffers/textures upload once; animation changes uniforms.
   The effect GLSL is shared verbatim with ISF exports. */
'use strict';
window.decoCreateProjection = function (gl, content, center, requestDraw) {
  let settings = {...content.settings}, ready = false, paused = false;
  let time = 0, last = null, frames = 0;
  const textures = [], ranges = [], loc = {};
  const effects = ['pulse', 'rings', 'checker', 'solid'];
  const coordinates = ['path', 'local_u', 'local_v', 'world_x', 'world_y', 'world_z', 'radial'];
  function compile(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source); gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS))
      throw new Error(gl.getShaderInfoLog(shader) || 'projection shader compilation failed');
    return shader;
  }
  const data = [];
  for (const face of content.faces) {
    const first = data.length / 8, role = face.role;
    let shift = [0, 0, 0];
    if (role === 'spine') shift = [0, Math.sign(face.positions[0][1] - center[1]) * .25, 0];
    if (role === 'rib' || role === 'armour') shift = [0, 0, 1];
    if (['closure', 'cap', 'blade', 'retainer'].includes(role)) shift = [0, 0, 2];
    for (let i = 0; i < face.positions.length; i++)
      data.push(...face.positions[i].map((v, k) => v - center[k]), ...face.uv[i], ...shift);
    ranges.push({first, count: data.length / 8 - first, id: face.instance_id});
  }
  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STATIC_DRAW);
  const vs = compile(gl.VERTEX_SHADER, `
    attribute vec3 aPosition, aShift;
    attribute vec2 aUV;
    varying vec2 vUV;
    uniform float uYaw, uPitch, uScaleX, uScaleY, uDepth, uExplode;
    void main() {
      vec3 p = aPosition + aShift * uExplode;
      float xx = cos(uYaw) * p.x + sin(uYaw) * p.z;
      float zz = -sin(uYaw) * p.x + cos(uYaw) * p.z;
      float yy = cos(uPitch) * p.y - sin(uPitch) * zz;
      float depth = sin(uPitch) * p.y + cos(uPitch) * zz;
      gl_Position = vec4(xx * uScaleX, yy * uScaleY, -depth * uDepth - 0.00002, 1.0);
      vUV = aUV;
    }`);
  const fs = compile(gl.FRAGMENT_SHADER, `
    precision highp float;
    varying vec2 vUV;
    uniform sampler2D localData, worldData, worldFineData, edgeData;
    uniform int effect, coordinate;
    uniform float speed, phase, repeats, width, softness, edgeWidth, brightness, seconds;
    uniform bool edgeOnly;
    uniform vec4 color, background;
    ${content.shader}
    void main() {
      vec4 local = texture2D(localData, vUV);
      vec4 world = texture2D(worldData, vUV);
      world.rgb = (255.0 * world.rgb + texture2D(worldFineData, vUV).rgb - 0.5) / 255.0;
      vec4 result = decoEffect(local, world, texture2D(edgeData, vUV), seconds);
      if (result.a < 0.001) discard;
      gl_FragColor = result;
    }`);
  const program = gl.createProgram();
  gl.attachShader(program, vs); gl.attachShader(program, fs); gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS))
    throw new Error(gl.getProgramInfoLog(program) || 'projection shader link failed');
  for (const name of ['uYaw', 'uPitch', 'uScaleX', 'uScaleY', 'uDepth', 'uExplode',
    'effect', 'coordinate', 'speed', 'phase', 'repeats', 'width', 'softness',
    'edgeWidth', 'brightness', 'seconds', 'edgeOnly', 'color', 'background'])
    loc[name] = gl.getUniformLocation(program, name);
  const attributes = ['aPosition', 'aUV', 'aShift'].map(name => gl.getAttribLocation(program, name));
  Promise.all(Object.entries(content.textures).map(([name, url], index) => new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const texture = gl.createTexture();
      gl.activeTexture(gl.TEXTURE0 + index); gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
      textures.push({name, index, texture}); resolve();
    };
    image.onerror = () => reject(new Error('Cannot load projection texture ' + url));
    image.src = url;
  }))).then(() => { ready = true; requestDraw(); }).catch(error => {
    document.getElementById('projectionStatus').textContent = error.message;
  });
  return {
    set(value) { settings = {...settings, ...value}; requestDraw(); },
    pause(value) { paused = value; last = null; requestDraw(); },
    active() { return ready && settings.enabled && !paused && settings.speed !== 0 && settings.effect !== 'solid'; },
    state() { return {settings, paused, frames, time, ready, renderer: 'webgl', bufferUploads: 1}; },
    draw(camera, hidden, now) {
      if (!ready || !settings.enabled) { last = null; return; }
      if (last !== null && !paused) time += Math.max(0, Math.min((now - last) / 1000, 0.1));
      last = now; frames++;
      gl.useProgram(program); gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      attributes.forEach((attribute, index) => {
        gl.enableVertexAttribArray(attribute);
        gl.vertexAttribPointer(attribute, [3, 2, 3][index], gl.FLOAT, false, 32, [0, 12, 20][index]);
      });
      for (const [name, value] of Object.entries(camera)) gl.uniform1f(loc[name], value);
      for (const name of ['speed', 'phase', 'repeats', 'width', 'softness', 'brightness'])
        gl.uniform1f(loc[name], settings[name]);
      gl.uniform1f(loc.seconds, time); gl.uniform1f(loc.edgeWidth, settings.edge_width);
      gl.uniform1i(loc.edgeOnly, settings.edge_only ? 1 : 0);
      gl.uniform1i(loc.effect, effects.indexOf(settings.effect));
      gl.uniform1i(loc.coordinate, coordinates.indexOf(settings.coordinate));
      gl.uniform4fv(loc.color, settings.color); gl.uniform4fv(loc.background, settings.background);
      for (const {name, index, texture} of textures) {
        gl.activeTexture(gl.TEXTURE0 + index); gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.uniform1i(gl.getUniformLocation(program, name), index);
      }
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); gl.depthMask(false);
      for (const range of ranges) if (!hidden.has(range.id))
        gl.drawArrays(gl.TRIANGLES, range.first, range.count);
      gl.depthMask(true); gl.disable(gl.BLEND);
    }
  };
};
