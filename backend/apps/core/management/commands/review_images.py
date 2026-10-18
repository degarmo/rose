"""Review site images that are hidden because they may show faces.

Interactive:   python manage.py review_images
List only:     python manage.py review_images --list
Scripted:      python manage.py review_images --set home-hero.webp=no-faces
"""

from django.core.management.base import BaseCommand, CommandError

from apps.core.manifest import find_entry, is_hidden, load_manifest, save_manifest

NO_FACES = "no-faces"
CONSENT = "consent"
KEEP = "keep-hidden"

CHOICES = {
    "n": NO_FACES,
    "c": CONSENT,
    "k": KEEP,
}

PROMPT = "  [n] no faces   [c] consent confirmed   [k] keep hidden   [q] save and quit: "


def apply_decision(entry, decision):
    if decision == NO_FACES:
        entry["faces_visible"] = False
        entry["consent_confirmed"] = False
    elif decision == CONSENT:
        entry["faces_visible"] = True
        entry["consent_confirmed"] = True
    elif decision != KEEP:
        raise CommandError(f"Unknown decision {decision!r}. Use {NO_FACES}, {CONSENT} or {KEEP}.")


class Command(BaseCommand):
    help = "List hidden manifest images and mark each as no faces, consent confirmed, or hidden."

    def add_arguments(self, parser):
        parser.add_argument("--list", action="store_true", help="List hidden images and exit.")
        parser.add_argument(
            "--set",
            action="append",
            default=[],
            metavar="FILENAME=DECISION",
            help=f"Apply a decision without prompting ({NO_FACES}, {CONSENT}, {KEEP}).",
        )

    def handle(self, *args, **options):
        manifest = load_manifest()
        hidden = [entry for entry in manifest["images"] if is_hidden(entry)]

        if options["set"]:
            self.apply_scripted(manifest, options["set"])
            return

        if not hidden:
            self.stdout.write(self.style.SUCCESS("No hidden images. Nothing to review."))
            return

        self.stdout.write(f"{len(hidden)} hidden image(s):\n")
        if options["list"]:
            for entry in hidden:
                self.describe(entry)
            return

        changed = 0
        for entry in hidden:
            self.describe(entry)
            decision = self.ask()
            if decision is None:
                break
            apply_decision(entry, decision)
            if decision != KEEP:
                changed += 1

        save_manifest(manifest)
        self.stdout.write(self.style.SUCCESS(f"Saved. {changed} image(s) updated."))

    def describe(self, entry):
        self.stdout.write(f"- {entry['filename']}")
        for label, key in (("source", "source"), ("credit", "credit"), ("from", "original_url")):
            if entry.get(key):
                self.stdout.write(f"    {label}: {entry[key]}")

    def ask(self):
        while True:
            answer = input(PROMPT).strip().lower()
            if answer == "q":
                return None
            if answer in CHOICES:
                return CHOICES[answer]
            self.stdout.write("  Please type n, c, k or q.")

    def apply_scripted(self, manifest, assignments):
        for assignment in assignments:
            filename, _, decision = assignment.partition("=")
            entry = find_entry(manifest, filename)
            if entry is None:
                raise CommandError(f"{filename} is not in the manifest.")
            apply_decision(entry, decision)
            self.stdout.write(f"{filename}: {decision}")
        save_manifest(manifest)
        self.stdout.write(self.style.SUCCESS("Saved."))
