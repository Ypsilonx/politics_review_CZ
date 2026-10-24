/* Světlý / tmavý režim a mobilní menu.
 * Načítá se synchronně v <head>: režim se nastaví na <html> dřív, než se stránka vykreslí.
 * Výchozí je tmavý režim; volba uživatele se pamatuje v localStorage. */
(function () {
  "use strict";

  var KLIC = "politika-rezim";

  /** Vrátí uložený režim ("light" / "dark"), nebo null, když není uložený nebo úložiště nejde číst. */
  function ulozenyRezim() {
    try { return localStorage.getItem(KLIC); } catch (e) { return null; }
  }

  /** Nastaví režim na <html data-theme> a pokusí se ho uložit. */
  function nastavRezim(rezim, ulozit) {
    document.documentElement.setAttribute("data-theme", rezim);
    if (ulozit) {
      try { localStorage.setItem(KLIC, rezim); } catch (e) { /* bez úložiště jen pro tuto stránku */ }
    }
  }

  nastavRezim(ulozenyRezim() || "dark", false);

  document.addEventListener("DOMContentLoaded", function () {
    var prepinac = document.querySelector("[data-prepnout-rezim]");
    if (prepinac) {
      prepinac.addEventListener("click", function () {
        var aktualni = document.documentElement.getAttribute("data-theme");
        nastavRezim(aktualni === "dark" ? "light" : "dark", true);
      });
    }

    var tlacitkoMenu = document.querySelector(".tlacitko-menu");
    if (tlacitkoMenu) {
      tlacitkoMenu.addEventListener("click", function () {
        var otevreno = tlacitkoMenu.getAttribute("aria-expanded") === "true";
        tlacitkoMenu.setAttribute("aria-expanded", String(!otevreno));
      });
    }
  });
})();
