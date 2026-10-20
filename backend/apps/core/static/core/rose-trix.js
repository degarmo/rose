// The admin's rich-text editor (Trix, with Unfold's settings). Unfold's paragraph block is
// grouped, so Trix put neighbouring paragraphs inside one <p> and joined them on save; each
// paragraph is its own block, as headings are.
window.Trix.config.blockAttributes.p.group = false;
