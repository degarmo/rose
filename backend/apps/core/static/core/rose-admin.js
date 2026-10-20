/*
 * Unfold's Alpine components, registered for Alpine's CSP build. That build never uses
 * eval or new Function, so it cannot reach page globals from an expression: Unfold's
 * helpers (defined in unfold/js/app.js) are handed to Alpine here instead.
 * Loaded before Alpine itself (templates/unfold/layouts/skeleton.html).
 */
document.addEventListener("alpine:init", () => {
  const helpers = { getCurrentTab, sortRecords, moveRecords };

  // The page's root: Unfold's theme and layout state, light unless chosen otherwise,
  // with the sidebar's resizing (templates/admin/nav_sidebar.html).
  window.Alpine.data("roseTheme", (initial = "light") => ({
    ...theme(initial),
    ...helpers,
    sidebarResizing: false,
    sidebarStyle() {
      return { width: `${this.sidebarWidth}px` };
    },
    resizeSidebar(event) {
      if (!this.sidebarResizing) return;
      this.sidebarWidth = Math.min(360, Math.max(220, event.clientX));
      localStorage.setItem("sidebarWidth", this.sidebarWidth);
    },
  }));
  // The body: the active tab of a change form, as Unfold's x-init set it, and the form's
  // action keeping that tab (templates/admin/change_form.html).
  window.Alpine.data("roseBody", (fallback = "") => ({
    activeTab: getCurrentTab() || fallback,
    formAction() {
      const here = window.location.pathname + window.location.search;
      return this.activeTab && this.activeTab !== "general" ? `${here}#${this.activeTab}` : here;
    },
  }));
  window.Alpine.data("searchCommand", searchCommand);
});
