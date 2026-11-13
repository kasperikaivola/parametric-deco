// Shared verbatim by the desktop WebGL renderer and generated ISF.
vec4 decoEffect(vec4 local, vec4 world, vec4 edge, float seconds) {
    float c = local.b;
    if (coordinate == 1) c = local.r;
    if (coordinate == 2) c = local.g;
    if (coordinate == 3) c = world.r;
    if (coordinate == 4) c = world.g;
    if (coordinate == 5) c = world.b;
    if (coordinate == 6 || effect == 1) c = length(world.rg - vec2(0.5));
    float moving = c * repeats - seconds * speed - phase;
    float delta = abs(fract(moving + 0.5) - 0.5);
    float feather = max(softness, 0.001);
    float level = 1.0 - smoothstep(width * 0.5, width * 0.5 + feather, delta);
    if (effect == 2) {
        float cells = mod(floor(local.r * repeats) + floor(local.g * repeats)
                          + floor(seconds * speed + phase), 2.0);
        level = cells;
    }
    if (effect == 3) level = 1.0;
    if (edgeOnly) level *= 1.0 - smoothstep(edgeWidth * 0.5, edgeWidth, edge.r);
    vec4 result = mix(background, color, level);
    return vec4(result.rgb * brightness, result.a * local.a);
}
