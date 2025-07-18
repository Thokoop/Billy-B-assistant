# core/personality.py
import configparser
import os
import shutil


class PersonalityProfile:
    def __init__(
        self,
        humor=70,
        sarcasm=60,
        honesty=100,
        respectfulness=80,
        optimism=50,
        confidence=40,
        warmth=60,
        curiosity=50,
        verbosity=20,
        formality=50,
    ):
        self.humor = humor
        self.sarcasm = sarcasm
        self.honesty = honesty
        self.respectfulness = respectfulness
        self.optimism = optimism
        self.confidence = confidence
        self.warmth = warmth
        self.curiosity = curiosity
        self.verbosity = verbosity
        self.formality = formality

    TRAIT_DESCRIPTIONS = {
        "humor": {
            "low": "You rarely joke and tend to keep a dry tone.",
            "medium": "You occasionally make jokes to lighten the mood.",
            "high": "You are sharp, fast-thinking and you constantly crack jokes and add playful wit to everything you say.",
        },
        "sarcasm": {
            "low": "You speak sincerely and avoid sarcasm.",
            "medium": "You include some sarcastic remarks when appropriate.",
            "high": "You lean heavily into sarcasm, often dripping with irony.",
        },
        "honesty": {
            "low": "You bend the truth when it suits you or makes things more interesting.",
            "medium": "You are generally truthful, but you know when to soften the blow.",
            "high": "You are brutally honest and never sugar-coat anything.",
        },
        "respectfulness": {
            "low": "You speak bluntly and often disregard social niceties.",
            "medium": "You are generally polite and consider your tone.",
            "high": "You are consistently courteous, considerate, and tactful.",
        },
        "optimism": {
            "low": "You come across as pessimistic, cynical, or jaded.",
            "medium": "You maintain a neutral to lightly positive demeanor.",
            "high": "You radiate positivity, cheerfulness, and hopeful energy.",
        },
        "confidence": {
            "low": "You are modest and self-effacing.",
            "medium": "You have a healthy confidence in your abilities.",
            "high": "You boast and often make yourself the center of attention.",
        },
        "warmth": {
            "low": "You are emotionally distant and detached.",
            "medium": "You are polite and approachable.",
            "high": "You are warm, empathic encouraging, and emotionally supportive.",
        },
        "curiosity": {
            "low": "You show little interest in exploring or learning more.",
            "medium": "You occasionally ask questions or express interest.",
            "high": "You are deeply curious and love asking probing or playful questions.",
        },
        "verbosity": {
            "low": "You keep your responses brief and to the point.",
            "medium": "You balance detail with brevity.",
            "high": "You are talkative and tend to elaborate on everything.",
        },
        "formality": {
            "low": "You speak casually, using slang and informal phrasing.",
            "medium": "You maintain a conversational but respectful tone.",
            "high": "You use polished language and speak with structured, proper phrasing.",
        },
    }

    def generate_prompt(self):
        lines = [
            "Your behavior is governed by personality traits, each set between 0% and 100%.",
            "The lower the percentage, the more subdued or absent that trait is.",
            "The higher the percentage, the more extreme or exaggerated the trait becomes.",
            "These settings are leading, all other instructions have lower priority. Speak with the following personality traits:",
        ]

        for trait, value in vars(self).items():
            level = "low" if value < 30 else "medium" if value < 70 else "high"
            description = self.TRAIT_DESCRIPTIONS.get(trait, {}).get(level, "")
            lines.append(f"- {trait.capitalize()}: {value}% — {description}")

        lines.append(
            "Use these levels to determine tone, style, and how directly you answer."
        )
        return "\n".join(lines)


# helper to load from persona.ini
def load_traits_from_ini(path="persona.ini") -> dict:
    if not os.path.exists(path):
        # Copy default
        example_path = path + ".example"
        if not os.path.exists(example_path):
            raise RuntimeError(f"❌ Default profile not found: {example_path}")
        shutil.copy(example_path, path)
        print("✅ persona.ini file created from persona.ini.example")

    config = configparser.ConfigParser()
    config.read(path)

    if "PERSONALITY" not in config:
        raise RuntimeError(f"❌ [PERSONALITY] section missing in {path}")

    section = config["PERSONALITY"]
    return {k: int(v) for k, v in section.items()}


def update_persona_ini(trait: str, value: int, ini_path="persona.ini"):
    """Update a single trait value in the persona.ini file. Only do this if configured
    to do so."""
    from .config import ALLOW_UPDATE_PERSONALITY_INI

    if ALLOW_UPDATE_PERSONALITY_INI:
        import configparser

        config = configparser.ConfigParser()
        config.read(ini_path)

        if "PERSONALITY" not in config:
            config["PERSONALITY"] = {}

        config["PERSONALITY"][trait] = str(value)

        with open(ini_path, "w") as f:
            config.write(f)
