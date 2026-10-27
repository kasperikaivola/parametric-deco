/*{
  "ISFVSN":"2",
  "DESCRIPTION":"Labelled face tiles: red +U, green +V; mapping belongs to Arena",
  "CATEGORIES":["Generator"],
  "INPUTS":[
    {"NAME":"calibrationImage","TYPE":"image"},
    {"NAME":"localData","TYPE":"image"},
    {"NAME":"grid","TYPE":"bool","DEFAULT":true}
  ]
}*/
void main() {
    vec4 data = IMG_NORM_PIXEL(localData, isf_FragNormCoord);
    vec4 cue = IMG_NORM_PIXEL(calibrationImage, isf_FragNormCoord);
    vec2 cell = abs(fract(data.rg * 10.0 + 0.5) - 0.5);
    float line = 1.0 - smoothstep(0.01, 0.03, min(cell.x, cell.y));
    vec3 rgb = mix(cue.rgb, vec3(1.0), grid ? line * 0.35 : 0.0);
    gl_FragColor = vec4(rgb, data.a);
}
