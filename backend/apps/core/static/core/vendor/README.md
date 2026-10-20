# Vendored scripts

- `alpine-csp-3.16.1.js`: the official Content Security Policy build of Alpine.js
  (`@alpinejs/csp@3.16.1`, MIT), the same version Unfold bundles. Unfold's own build
  evaluates expressions with `new Function`, which the site's policy forbids; this one
  does not. Loaded by `templates/unfold/layouts/skeleton.html` in its place.
