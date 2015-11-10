uniform mat3 transformation_matrix;
uniform sampler2D color_buffer;

#define PI  3.14159265

vec2 world2equirectangular(vec3 vert)
{
    float theta = asin(vert.z);
    float phi = atan(vert.x, vert.y);

    float u = 0.5 * (phi / PI) + 0.25;
    float v = 0.5 + theta/PI;

    return vec2(u,v);
}


vec3 equirectangular2world(vec2 coords)
{
    float u = coords.s;
    float v = coords.t;

    float phi = (0.5 - u) * 2.0 * PI;
    float theta = (v - 0.5) * PI;
    float r = cos(theta);

    float x = cos(phi) * r;
    float y = sin(phi) * r;
    float z = sin(theta);

    return vec3(x, y, z);
}

void main()
{
    vec2 coords = gl_TexCoord[0].st;
    vec3 source = equirectangular2world(coords);
    vec3 world = transformation_matrix * source;

    vec2 uv = world2equirectangular(world);

    gl_FragColor.rgb = texture2D(color_buffer, uv).rgb;
    gl_FragColor.a = 1.0;
}
