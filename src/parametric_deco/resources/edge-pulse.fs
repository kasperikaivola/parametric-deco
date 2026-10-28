/*{
  "ISFVSN": "2",
  "DESCRIPTION": "A cross-part phase pulse on real surface edges; unmapped atlas output",
  "CATEGORIES": ["Generator"],
  "INPUTS": [
    {"NAME":"localData","TYPE":"image"},
    {"NAME":"edgeData","TYPE":"image"},
    {"NAME":"speed","TYPE":"float","DEFAULT":0.1,"MIN":-2.0,"MAX":2.0},
    {"NAME":"phase","TYPE":"float","DEFAULT":0.0,"MIN":0.0,"MAX":1.0},
    {"NAME":"color","TYPE":"color","DEFAULT":[0.2,0.7,1.0,1.0]},
    {"NAME":"width","TYPE":"float","DEFAULT":0.05,"MIN":0.0,"MAX":0.5}
  ]
}*/
void main() {
    vec4 data = IMG_NORM_PIXEL(localData, isf_FragNormCoord);
    vec4 edge = IMG_NORM_PIXEL(edgeData, isf_FragNormCoord);
    float w = max(width, 0.00001);
    float delta = abs(fract(data.b - TIME * speed - phase + 0.5) - 0.5);
    float pulse = 1.0 - smoothstep(w * 0.5, w, delta);
    float line = 1.0 - smoothstep(0.01, 0.04, edge.r);
    gl_FragColor = vec4(color.rgb * pulse * line, color.a * data.a);
}
