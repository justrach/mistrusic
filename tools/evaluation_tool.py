import os
import json
from smolagents import Tool


EVAL_PROMPT = """You are an expert audio engineer evaluating an audio transformation. Compare the original and morphed features and assess quality.

## Original Audio Features:
{original_features}

## Morphed Audio Features:
{morphed_features}

## Target Description:
{target_description}

## Evaluation Criteria:
1. Is the output non-silent? (RMS must be > 0.01 — if below, score 1)
2. Is the duration similar to original? (if drastically shorter, penalize)
3. Did spectral characteristics change meaningfully? (compare centroid, MFCC)
4. Does the transformation direction match the intent?
5. Would this sound interesting and pleasing to a listener?

## Scoring Guide:
- 1-3: Broken output (silent, clipping, or completely wrong direction)
- 4-5: Audible change but sounds bad or doesn't match intent well
- 6: Decent attempt but needs refinement for good quality
- 7-8: Good result that matches the intent
- 9-10: Excellent, creative, compelling transformation

Be strict but fair. Most single-pass transformations deserve 4-6. Multi-step chained transformations with good blending deserve 7+.

## IMPORTANT: Give specific, actionable suggestions using the exact tool names:
- "Try spectral_imprint with smoothing=0.6 for a smoother blend"
- "Mix the result with the original using mix_audio at ratio=0.3 to retain clarity"
- "Add convolution with wet_dry=0.25 for subtle spatial depth"
- "Try cross_synthesize instead for a more dramatic morph"

Respond with ONLY a JSON object:
{{"score": <int 1-10>, "reasoning": "<why this score>", "suggestions": ["<specific tool call suggestion>", ...]}}
"""


class EvaluateMorphTool(Tool):
    name = "evaluate_morph"
    description = """Evaluates the quality of an audio transformation by comparing original and morphed audio features against the target description. Uses Mistral AI to reason about whether the transformation achieved the intended goal. Returns a JSON with score (1-10), reasoning, and improvement suggestions. Call this after every transformation step to decide whether to refine."""
    inputs = {
        "original_features": {
            "type": "string",
            "description": "JSON string of original audio features (from extract_audio_features)",
        },
        "morphed_features": {
            "type": "string",
            "description": "JSON string of morphed audio features (from extract_audio_features)",
        },
        "target_description": {
            "type": "string",
            "description": "What the transformation was supposed to achieve",
        },
    }
    output_type = "string"

    def forward(self, original_features: str, morphed_features: str, target_description: str) -> str:
        from mistralai import Mistral

        client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

        prompt = EVAL_PROMPT.format(
            original_features=original_features,
            morphed_features=morphed_features,
            target_description=target_description,
        )

        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()
        # Try to parse as JSON, return as-is if valid
        try:
            parsed = json.loads(content)
            return json.dumps(parsed)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(content[start:end])
                    return json.dumps(parsed)
                except json.JSONDecodeError:
                    pass
            return json.dumps({
                "score": 5,
                "reasoning": content,
                "suggestions": ["Could not parse evaluation response, consider retrying"],
            })
