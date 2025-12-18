"""Templated prompts for consistent AI generation."""

# Cultural elements to preserve
AFRICAN_MOTIFS = [
    "Adinkra symbols",
    "Kente weaving patterns",
    "Ankara/African wax print designs",
    "Bogolan/mud cloth patterns",
    "Ndebele geometric patterns",
    "Zulu beadwork designs",
    "Maasai color schemes",
]

# Base prompts for different operations
BREEDING_PROMPT_TEMPLATE = """
Create a hybrid design by blending the provided images.

Blend the visual elements proportionally:
{weight_descriptions}

Guidelines:
- Combine patterns, textures, and color schemes harmoniously
- Maintain visual coherence in the final design
- Preserve any African cultural motifs present: {motifs}

{additional_instructions}
"""

REFINING_PROMPT_TEMPLATE = """
Refine and enhance this design with the following instructions:
{user_prompt}

Refinement settings:
- Intensity: {strength}%
- Preserve core structure: Yes
- Maintain cultural authenticity: Yes

Focus areas:
- Enhance visual quality and detail
- Apply requested stylistic changes
- Preserve African design elements: {motifs}
"""

EDITING_PROMPT_TEMPLATES = {
    "inpaint": """
Fill the masked region with content that:
- Matches the surrounding style and patterns
- Follows these instructions: {prompt}
- Maintains cultural coherence with the overall design
""",
    
    "style_transfer": """
Apply the following style transformation:
{prompt}

Maintain:
- Core composition and layout
- African cultural motifs if present
- Visual harmony with untransformed areas
""",
    
    "color_swap": """
Adjust the colors as follows:
{prompt}

Ensure:
- New palette remains harmonious
- Cultural color symbolism is respected
- Contrast and readability are maintained
""",
}


def build_breeding_prompt(
    weights: list[tuple[str, float]],
    additional_prompt: str = "",
    preserve_cultural: bool = True,
) -> str:
    """Build a breeding prompt with weight descriptions."""
    weight_desc = [f"- Image {i+1}: {w*100:.0f}% influence" for i, (_, w) in enumerate(weights)]
    
    motifs = ", ".join(AFRICAN_MOTIFS[:4]) if preserve_cultural else "N/A"
    
    return BREEDING_PROMPT_TEMPLATE.format(
        weight_descriptions="\n".join(weight_desc),
        motifs=motifs,
        additional_instructions=additional_prompt,
    )


def build_refining_prompt(
    user_prompt: str,
    strength: float = 0.7,
    preserve_cultural: bool = True,
) -> str:
    """Build a refining prompt."""
    motifs = ", ".join(AFRICAN_MOTIFS[:4]) if preserve_cultural else "N/A"
    
    return REFINING_PROMPT_TEMPLATE.format(
        user_prompt=user_prompt,
        strength=int(strength * 100),
        motifs=motifs,
    )


def build_editing_prompt(
    edit_type: str,
    user_prompt: str,
) -> str:
    """Build an editing prompt based on edit type."""
    template = EDITING_PROMPT_TEMPLATES.get(edit_type, EDITING_PROMPT_TEMPLATES["inpaint"])
    return template.format(prompt=user_prompt)
