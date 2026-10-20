"""Admin widgets in Rose's look."""

from unfold.contrib.forms.widgets import WysiwygWidget


class RichTextWidget(WysiwygWidget):
    """Unfold's editor, keeping each paragraph separate (core/rose-trix.js)."""

    class Media:
        # Listed with Unfold's two, so the change comes after its settings.
        js = ("unfold/forms/js/trix/trix.js", "unfold/forms/js/trix.config.js", "core/rose-trix.js")
