/* Mapa regionálních kanceláří: Leaflet + OpenStreetMap, shlukování bodů, filtr podle klubu.
 * Data přicházejí v <script id="data-kancelari" type="application/json"> (bez dalšího požadavku). */
(function () {
  "use strict";

  var STRED_CR = [49.8, 15.5];
  var PRIBLIZENI_CR = 7;

  var data = JSON.parse(document.getElementById("data-kancelari").textContent);
  var mapa = L.map("mapa", { scrollWheelZoom: true }).setView(STRED_CR, PRIBLIZENI_CR);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(mapa);

  /** Vytvoří obsah bubliny kanceláře bez innerHTML z dat (jméno a adresa jako text). */
  function bublina(k) {
    var obal = document.createElement("div");
    var odkaz = document.createElement("a");
    odkaz.href = "/poslanec/" + k.id_poslanec;
    odkaz.textContent = k.jmeno;
    var klub = document.createElement("div");
    klub.className = "tlumene";
    klub.textContent = k.klub;
    var adresa = document.createElement("div");
    adresa.textContent = k.adresa;
    obal.append(odkaz, klub, adresa);
    return obal;
  }

  var shluky = L.markerClusterGroup({ showCoverageOnHover: false });
  var znacky = data.kancelare.map(function (k) {
    var znacka = L.marker([k.lat, k.lng], { title: k.jmeno }).bindPopup(bublina(k));
    znacka.kancelar = k;
    return znacka;
  });
  mapa.addLayer(shluky);

  /** Zobrazí jen kanceláře zvoleného klubu (prázdná volba = všechny). */
  function filtruj(klub) {
    shluky.clearLayers();
    shluky.addLayers(znacky.filter(function (z) { return !klub || z.kancelar.klub === klub; }));
  }

  filtruj("");
  document.querySelector("#filtr-mapy select").addEventListener("change", function (e) {
    filtruj(e.target.value);
  });

  if (data.osoba) {
    var hledana = znacky.find(function (z) { return z.kancelar.id_osoba === data.osoba; });
    if (hledana) {
      shluky.zoomToShowLayer(hledana, function () { hledana.openPopup(); });
    }
  }
})();
