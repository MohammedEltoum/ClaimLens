"""Generated sample tickets used by the Gradio UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_IMAGE_PATH = PROJECT_ROOT / "radio2.png"
EXAMPLE_IMAGE_DIR = PROJECT_ROOT / "examples" / "images"
SAMPLE_COMPLAINT = (
    "The radio arrived with the front casing cracked and one of the knobs loose. "
    "I bought it as a birthday gift and need a replacement sent as soon as possible."
)


@dataclass(frozen=True)
class SupportExample:
    label: str
    image_path: Path
    complaint: str

    def as_gradio_row(self) -> list[str]:
        return [str(self.image_path), self.complaint]


SUPPORT_EXAMPLES = [
    SupportExample(
        "Cracked radio - replacement",
        SAMPLE_IMAGE_PATH,
        SAMPLE_COMPLAINT,
    ),
    SupportExample(
        "Headphones in good condition",
        EXAMPLE_IMAGE_DIR / "headphones-good.png",
        "The headphones arrived with a cracked headband and the left ear cushion is torn open. I need a replacement.",
    ),
    SupportExample(
        "Headphones torn and cracked",
        EXAMPLE_IMAGE_DIR / "headphones-defective.png",
        "The headphones arrived with a cracked headband and the left ear cushion is torn open. I need a replacement.",
    ),
    SupportExample(
        "Mug in good condition",
        EXAMPLE_IMAGE_DIR / "mug-good.png",
        "The mug arrived with a chipped rim and a crack down the side. I would like a refund.",
    ),
    SupportExample(
        "Mug chipped and cracked",
        EXAMPLE_IMAGE_DIR / "mug-defective.png",
        "The mug arrived with a chipped rim and a crack down the side. I would like a refund.",
    ),
    SupportExample(
        "Watch in good condition",
        EXAMPLE_IMAGE_DIR / "watch-good.png",
        "The smartwatch screen is cracked out of the box and I am worried it may cut my finger. Please escalate this.",
    ),
    SupportExample(
        "Watch cracked screen",
        EXAMPLE_IMAGE_DIR / "watch-defective.png",
        "The smartwatch screen is cracked out of the box and I am worried it may cut my finger. Please escalate this.",
    ),
]
