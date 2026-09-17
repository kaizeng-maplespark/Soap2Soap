"""
Compiles t2i and i2v prompts for each shot, then rewrites them into the target style.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from v2.core.schema import Shot

STYLE_PREFIXES = {
    "realistic":      "Photorealistic cinematic style. Shot on 35mm film.",
    "cinefilter":     "Premium live-action feature-film finish. Preserve source content and geometry while improving cinematic image formation.",
    "disney":         "Disney 3D animated movie style. Vibrant colors, expressive characters, polished CG render.",
    "pixar":          "Pixar 3D animated movie style. Warm soft lighting, subsurface skin glow, richly detailed environments, emotionally expressive characters with realistic proportions.",
    "anime":          "Japanese anime style. Clean linework, vivid colors, cinematic composition.",
    "japanese_anime": "Japanese manga/anime style. Clean lines, dynamic composition, expressive faces.",
    "clay":           "Claymation stop-motion style. Visible clay texture, warm handcrafted look.",
    "lego":           "LEGO brick animation style. Blocky figures, bright primary colors, plastic sheen.",
    "family_guy":     "American adult animated TV style. Flat colors, clean outlines, comedic proportions.",
}

STYLE_REWRITE_GUIDES = {
    "realistic": "Keep the prompt as-is. It is already in photorealistic cinematic language.",
    "cinefilter": (
        "Preserve the original subject identity, facial features, clothing, objects, action, timing, composition, camera position, camera movement and scene geometry. "
        "Do not redesign or restage the shot. Improve only the photographic rendering: dimensional motivated lighting, natural subject separation, realistic skin and material microtexture, rich tonal depth, soft highlight roll-off, detailed non-crushed shadows, restrained saturation, subtle warm-cool separation, natural local contrast, atmospheric depth, realistic lens rendering, restrained practical-light bloom, coherent motion rendering and fine organic film texture. "
        "Avoid plastic skin, synthetic sharpening, excessive HDR, crushed blacks, oversaturation, fake bokeh, exaggerated teal-orange grading, excessive bloom and heavy grain. "
        "The result should feel photographed rather than generated: expensive, restrained, naturalistic and production-ready."
    ),
    "disney": "Rewrite using Disney 3D animated movie language. Characters become expressive 3D-animated Disney figures with rounded features, big eyes, and smooth polished CG surfaces. Environments become vibrant, colorful, and painterly.",
    "pixar": "Rewrite using Pixar 3D animated movie language. Characters become Pixar-style 3D figures with soft subsurface skin glow, richly detailed clothing and expressive faces. Environments are warmly lit, physically detailed and cinematic.",
    "anime": "Rewrite using Japanese anime visual language. Characters become anime-style with clean linework, large expressive eyes, and stylized proportions. Environments use flat, vivid colors with detailed linework.",
    "japanese_anime": "Rewrite using Japanese manga/anime language. Characters have exaggerated proportions, expressive faces and dynamic poses.",
    "clay": "Rewrite using claymation stop-motion language. Characters become clay figures with visible fingerprint texture, slightly imperfect shapes and handcrafted warmth. Environments are made of clay, fabric and foam.",
    "lego": "Rewrite using LEGO animation language. Characters become LEGO minifigures and environments are built from colorful LEGO bricks and plates.",
    "family_guy": "Rewrite using Family Guy 2D animation language. Characters become flat-colored cartoon figures with thick black outlines and comedic proportions.",
}

_STYLE_REWRITE_PROMPT = """Rewrite the following image/video generation prompt to match the target visual style.

TARGET STYLE: {style_name}
STYLE GUIDE: {style_guide}

ORIGINAL PROMPT:
{prompt}

Rules:
- Rewrite ALL character and environment descriptions using the target style language
- Keep ALL @character_XX tokens exactly as written — do NOT replace or remove them
- Keep camera parameters (shot size, lens mm, camera angle, depth of field, composition)
- Keep dialogue references if present
- Output ONLY the rewritten prompt text, no explanation, no markdown, no prefix
"""

_CINEFILTER_REWRITE_PROMPT = """You are a feature-film finishing cinematographer. Transform the prompt into a CONTENT-PRESERVING cinematic finishing instruction.

ORIGINAL SHOT DESCRIPTION:
{prompt}

FINISHING STRENGTH: {strength}

Non-negotiable preservation rules:
- Preserve subject identity and facial features.
- Preserve clothing, props, text, objects and environment identity.
- Preserve action, timing, pose, composition, framing, camera position, camera movement and scene geometry.
- Do not add, remove, replace, redesign or restage anything.
- Do not beautify or alter age/body/face.

Improve only photographic appearance using scene-appropriate choices: dimensional motivated lighting, realistic skin/material microtexture, tonal depth, soft highlight roll-off, non-crushed shadow detail, restrained saturation, sophisticated but natural color separation, local contrast, atmospheric depth, realistic lens rendering, subtle practical-light bloom, coherent motion rendering and fine organic film texture.

Avoid: plastic skin, synthetic sharpness, excessive HDR, crushed blacks, oversaturation, fake bokeh, exaggerated teal-orange, excessive bloom, heavy grain, fantasy relighting, new light sources, changed weather or changed time of day.

Strength semantics:
- faithful: subtle tone/color/texture finishing; source appearance remains dominant.
- balanced: stronger cinematic tone, material, depth and lighting polish while preserving content exactly.
- strong: maximum photographic reinterpretation that still preserves identity, objects, action, framing and geometry.

Output ONLY the final generation prompt, no explanation or markdown.
"""

_STYLE_I2V_REWRITE_PROMPT = """Add a brief visual style qualifier to the following video generation prompt.

TARGET STYLE: {style_name}
STYLE QUALIFIER: {style_qualifier}

ORIGINAL PROMPT (characters already described in natural language):
{prompt}

Rules:
- Prepend a SHORT style label
- Keep the original action and scene description EXACTLY — do NOT expand, rephrase, or embellish
- Do NOT invent new details, objects, or character behaviors not in the original
- Keep all character names as-is
- Keep camera notes as-is
- Output ONLY the final prompt, no explanation, 1-3 sentences max
"""

_I2V_STYLE_QUALIFIERS = {
    "clay": "Claymation stop-motion animation. Handcrafted clay figures, visible texture.",
    "pixar": "Pixar 3D animated film. Warm lighting, expressive characters.",
    "disney": "Disney 3D animated film. Vibrant colors, polished CG.",
    "anime": "Japanese anime style. Clean linework, expressive.",
    "japanese_anime": "Japanese manga/anime style. Dynamic, expressive.",
    "lego": "LEGO brick animation. Blocky minifigures, plastic sheen.",
    "family_guy": "Family Guy 2D cartoon. Flat colors, thick outlines.",
    "realistic": "",
    "cinefilter": "Premium live-action feature-film finish. Preserve source content exactly.",
}


def _rewrite_for_style(prompt: str, style: str, finishing_strength: str = "balanced") -> str:
    if style == "realistic":
        return prompt
    from v2.clients.gemini_client import text_generate
    if style == "cinefilter":
        rewrite_prompt = _CINEFILTER_REWRITE_PROMPT.format(prompt=prompt, strength=finishing_strength)
    else:
        guide = STYLE_REWRITE_GUIDES.get(style, STYLE_REWRITE_GUIDES["realistic"])
        rewrite_prompt = _STYLE_REWRITE_PROMPT.format(style_name=style.upper(), style_guide=guide, prompt=prompt)
    try:
        result = text_generate(rewrite_prompt)
        return result.strip() if result and result.strip() else prompt
    except Exception:
        return prompt


def _rewrite_i2v_for_style(prompt: str, style: str, finishing_strength: str = "balanced") -> str:
    if style == "realistic":
        return prompt
    from v2.clients.gemini_client import text_generate
    if style == "cinefilter":
        rewrite_prompt = _CINEFILTER_REWRITE_PROMPT.format(prompt=prompt, strength=finishing_strength)
    else:
        qualifier = _I2V_STYLE_QUALIFIERS.get(style, "")
        if not qualifier:
            return prompt
        rewrite_prompt = _STYLE_I2V_REWRITE_PROMPT.format(style_name=style.upper(), style_qualifier=qualifier, prompt=prompt)
    try:
        result = text_generate(rewrite_prompt)
        return result.strip() if result and result.strip() else prompt
    except Exception:
        return prompt


def compile_t2i_prompt(shot: "Shot", style: str = "realistic", finishing_strength: str = "balanced") -> str:
    lines = []
    if shot.t2i_prompt: lines.append(shot.t2i_prompt)
    if shot.environment_description: lines.append(f"Environment: {shot.environment_description}")
    if shot.lighting_setup: lines.append(f"Lighting: {shot.lighting_setup}")
    if shot.color_grading: lines.append(f"Color grading: {shot.color_grading}")
    if shot.shot_size: lines.append(f"Shot size: {shot.shot_size}")
    if shot.camera_angle: lines.append(f"Camera angle: {shot.camera_angle}")
    if shot.focal_length: lines.append(f"Lens: {shot.focal_length}")
    if shot.depth_of_field: lines.append(f"Depth of field: {shot.depth_of_field}")
    if shot.mood_atmosphere: lines.append(f"Mood: {shot.mood_atmosphere}")
    if shot.composition: lines.append(f"Composition: {shot.composition}")
    return _rewrite_for_style("\n".join(lines), style, finishing_strength)


def _detect_language(texts: list[str]) -> str:
    for t in texts:
        if any('\u4e00' <= c <= '\u9fff' for c in t): return 'zh'
    return 'en'


def _build_char_alias(description: str) -> str:
    import re
    desc = description or ""
    if "Female" in desc:
        gender = "woman" if "Age: 3" in desc or "Age: 4" in desc or "Age: 5" in desc else "girl"
        if re.search(r"Age:\s*\d?[5-9][-–]", desc) or "Age: 5" in desc or "Age: 6" in desc: gender = "girl"
    elif "Male" in desc:
        gender = "man"
        if re.search(r"Age:\s*[5-9]\b|\bAge:\s*\d\b", desc): gender = "boy"
    else: gender = "person"
    clothing_match = re.search(r"Clothing:\s*([^.]+)", desc)
    clothing = ""
    if clothing_match:
        raw = clothing_match.group(1).strip()
        first_item = re.split(r",| and | with | over | worn", raw)[0].strip()
        clothing = " ".join(first_item.split()[:5]).rstrip(".,;")
    return f"the {gender} in {clothing.lower()}" if clothing else f"the {gender}"


def build_char_alias_map(characters) -> dict:
    return {c.id: _build_char_alias(c.description) for c in characters}


def resolve_char_tokens(text: str, alias_map: dict) -> str:
    for char_id, alias in alias_map.items(): text = text.replace(char_id, alias)
    return text


def compile_i2v_prompt(shot: "Shot", style: str = "realistic", dialogue_lang: str = "auto",
                       char_alias_map: dict = None, finishing_strength: str = "balanced") -> str:
    import re
    base = shot.i2v_prompt or shot.t2i_prompt or "A cinematic shot."
    base = re.sub(r"\s*台词：.*$", "", base).strip()
    motion_note = f" Action: {shot.subject_movement}." if shot.subject_movement else ""
    if shot.camera_movement: motion_note += f" Camera: {shot.camera_movement}."
    raw_scene = f"{base}{motion_note}"
    if char_alias_map: raw_scene = resolve_char_tokens(raw_scene, char_alias_map)
    styled_scene = _rewrite_i2v_for_style(raw_scene, style, finishing_strength)
    OFF_SCREEN_SPEAKERS = {"旁白", "背景音", "街边群众"}
    dialogue_note = ""
    if shot.dialogue:
        lang = _detect_language([d.text for d in shot.dialogue]) if dialogue_lang == "auto" else dialogue_lang
        alias = char_alias_map or {}
        on_screen = [d for d in shot.dialogue if d.speaker_id not in OFF_SCREEN_SPEAKERS]
        off_screen = [d for d in shot.dialogue if d.speaker_id in OFF_SCREEN_SPEAKERS]
        parts = []
        if off_screen:
            if lang == "zh":
                lines = "；".join(f'{d.speaker_id}："{d.text}"' for d in off_screen)
                parts.append(f"画外音（off-screen voiceover ONLY, no visible character speaks）：{lines}。")
            else:
                lines = "; ".join(f'{d.speaker_id}: "{d.text}"' for d in off_screen)
                parts.append(f"Off-screen voiceover (NOT spoken by any visible character): {lines}.")
        if on_screen:
            if lang == "zh":
                lines = "；".join(f'{alias.get(d.speaker_id, d.speaker_id)}说："{d.text}"' for d in on_screen)
                parts.append(f"对话内容（必须严格使用中文原文发音）：{lines}。")
            else:
                lines = "; ".join(f'{alias.get(d.speaker_id, d.speaker_id)} says: "{d.text}"' for d in on_screen)
                parts.append(f"Spoken dialogue (preserve original language exactly): {lines}.")
        dialogue_note = " " + " ".join(parts)
    return f"{styled_scene}{dialogue_note}"
