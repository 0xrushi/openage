#version 330

in vec2 vert_uv;

layout(location=0) out vec4 col;
layout(location=1) out uint id;

uniform sampler2D tex;
uniform uint u_id;
uniform uint u_owner;

// position (top left corner) and size: (x, y, width, height)
uniform vec4 tile_params;

vec2 uv = vec2(
	vert_uv.x * tile_params.z + tile_params.x,
	vert_uv.y * tile_params.w + tile_params.y
);

// Player team colors (8 players).
vec3 player_colors[8] = vec3[8](
	vec3(0.0f, 0.0f, 1.0f),   // player 0: blue
	vec3(1.0f, 0.0f, 0.0f),   // player 1: red
	vec3(0.0f, 1.0f, 0.0f),   // player 2: green
	vec3(1.0f, 1.0f, 0.0f),   // player 3: yellow
	vec3(0.0f, 1.0f, 1.0f),   // player 4: cyan
	vec3(1.0f, 0.0f, 1.0f),   // player 5: magenta
	vec3(1.0f, 0.5f, 0.0f),   // player 6: orange
	vec3(0.5f, 0.0f, 0.5f)    // player 7: purple
);

void main() {
	vec4 tex_val = texture(tex, uv);
	int alpha = int(round(tex_val.a * 255));
	switch (alpha) {
		case 0:
			col = tex_val;
			discard;

			// do not save the ID
			return;
		case 254:
		case 252:
		case 250:
			// Player color pixels: use owner to pick team color.
			uint idx = u_owner % 8u;
			vec3 base = player_colors[idx];
			// Vary brightness based on the alpha marker.
			float brightness = 1.0f;
			if (alpha == 252) brightness = 0.75f;
			if (alpha == 250) brightness = 0.5f;
			col = vec4(base * brightness, 1.0f);
			break;
		default:
			col = tex_val;
			break;
	}
	id = u_id;
}
