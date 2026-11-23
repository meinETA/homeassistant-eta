/* ETA Heating – plant overview card (prototype). */
(() => {
  const W = 1600;
  const H = 860;
  const FLOOR = 610;
  // bump when icon files change, so browsers do not keep stale images
  const ICON_REV = "2026-11-23a";

  // type -> [icon file, icon width on the 1600px canvas, aspect w/h]
  const ICONS = {
    silo: ["Austragungen_Befuellungen/Pelletslager/Pelletslager.webp", 290, 1.4206],
    chip_store: ["Austragungen_Befuellungen/Hack_Austragung/Ruehrwerk.webp", 290, 1],
    boiler: ["Kessel/Pellets/PU_PC_neu.webp", 290, 904 / 924],
    buffer: ["FUBs/PufferFlex/Puffer.webp", 230, 720 / 1040],
    heating_circuit: ["FUBs/Heizkreise/Radiator_ein.webp", 230, 640 / 400],
    fwm: ["FUBs/FWM/FWM.webp", 250, 1080 / 860],
    dhw: ["FUBs/Warmwasser/WW.webp", 200, 720 / 1040],
    external_demand: ["FUBs/Externe_Waermeanforderung/Externe_Waermeanforderung.webp", 220, 1000 / 684],
    solar: ["FUBs/Solar/Solar.webp", 240, 1],
    unknown: ["FUBs/System/System.webp", 170, 1200 / 1000],
    external_heat: ["FUBs/System/System.webp", 170, 1200 / 1000],
  };
  // selectable icons per block type: [label, file, aspect w/h]
  const STORE_CHOICES = [
      ["Pelletslager", "Austragungen_Befuellungen/Pelletslager/Pelletslager.webp", 1557 / 1096],
      ["Saugsystem 3-fach", "Austragungen_Befuellungen/Pellets_Umschalteinheit/3fach.webp", 300 / 300],
      ["Saugsystem 4-fach", "Austragungen_Befuellungen/Pellets_Umschalteinheit/4fach.webp", 300 / 300],
      ["Saugsystem 8-fach", "Austragungen_Befuellungen/Pellets_Umschalteinheit/8fach.webp", 300 / 300],
      ["Hackgut Rührwerk", "Austragungen_Befuellungen/Hack_Austragung/Ruehrwerk.webp", 1200 / 1200],
      ["Hackgut Schnecke", "Austragungen_Befuellungen/Hack_Austragung/Schnecke.webp", 300 / 300],
      ["Rührer", "Austragungen_Befuellungen/Ruehrer/Ruehrer.webp", 300 / 300],
      ["Pendelschnecke", "Austragungen_Befuellungen/Pendelschnecke/Grundbild_1er.webp", 300 / 300],
      ["Pendelschnecke 2-fach", "Austragungen_Befuellungen/Pendelschnecke/Grundbild_2er.webp", 300 / 300],
      ["Schubboden", "Austragungen_Befuellungen/Schubboden/Schubboden_1er.webp", 300 / 300],
      ["Schubboden 2-fach", "Austragungen_Befuellungen/Schubboden/Schubboden_2er.webp", 300 / 300],
      ["Schubboden 3-fach", "Austragungen_Befuellungen/Schubboden/Schubboden_3er.webp", 300 / 300],
  ];
  // other heat sources the ETA controls (object 10281 "Brenner") or parts the card does not know
  const HEAT_CHOICES = [
    ["Modul", "FUBs/System/System.webp", 1200 / 1000],
    ["Wärmepumpe", "Kessel/Brenner/Waermepumpe_ein.webp", 540 / 440],
    ["Öl-/Gasbrenner", "Kessel/Brenner/Brenner_ein.webp", 540 / 440],
    ["Biomasse", "Kessel/Brenner/Biomasse_ein.webp", 540 / 440],
  ];
  const ICON_CHOICES = {
    unknown: HEAT_CHOICES,
    external_heat: HEAT_CHOICES,
    silo: STORE_CHOICES,
    chip_store: STORE_CHOICES,
    boiler: [
      ["PU / PC", "Kessel/Pellets/PU_PC_neu.webp", 904 / 924],
      ["PU / PC grau", "Kessel/Pellets/PU_PC_grau.webp", 904 / 924],
      ["PE-K", "Kessel/Pellets/PEK.webp", 840 / 1000],
      ["ePE-K", "Kessel/Pellets/ePEK.webp", 884 / 932],
      ["ePE (gelb)", "Kessel/ePE/ePE_HW.webp", 904 / 924],
      ["ePE (Einblick)", "Kessel/ePE/ePE_einblick.webp", 904 / 924],
      ["ePE BW (weiß)", "Kessel/ePE_BW/ePE_BW.webp", 560 / 880],
      ["SH", "Kessel/SH/SH_neu.webp", 780 / 980],
      ["SH alt", "Kessel/SH/SH.webp", 780 / 980],
      ["SH-TWIN", "Kessel/TWIN/SH_TWIN_neu.webp", 1020 / 920],
      ["SH-TWIN alt", "Kessel/TWIN/SH_TWIN.webp", 1020 / 920],
      ["eSH (P3)", "Kessel/eSH/FUB_eSH_BE-P3.webp", 904 / 900],
      ["eSH (P4)", "Kessel/eSH/FUB_eSH_BE-P4.webp", 1132 / 1124],
      ["eSH-TWIN (P3)", "Kessel/eSH_eTWIN/FUB_eSH-eTWIN_BE-P3.webp", 904 / 900],
      ["eSH-TWIN (P4)", "Kessel/eSH_eTWIN/FUB_eSH-eTWIN_BE-P4.webp", 1132 / 1124],
      ["eTWIN (P3)", "Kessel/eTWIN/FUB_eTWIN_BE-P3.webp", 904 / 900],
      ["eTWIN (P4)", "Kessel/eTWIN/FUB_eTWIN_BE-P4.webp", 1132 / 1124],
      ["eHACK", "Kessel/eHack/eHack.webp", 1000 / 1000],
      ["HACK", "Kessel/Hack/Hack.webp", 1000 / 1000],
      ["HACK VR (gelb)", "Kessel/HackVR/HackVR_gelb.webp", 1180 / 900],
      ["HACK VR (grau)", "Kessel/HackVR/HackVR_grau.webp", 1180 / 900],
    ],
    buffer: [
      ["Puffer", "FUBs/PufferFlex/Puffer.webp", 720 / 1040],
      ["Puffer mit Wendel", "FUBs/PufferFlex/Puffer_Wendel.webp", 720 / 1040],
      ["Kombispeicher", "FUBs/PufferFlex/Kombi.webp", 300 / 300],
    ],
    heating_circuit: [
      ["Heizkörper", "FUBs/Heizkreise/Radiator_ein.webp", 640 / 400],
      ["Fußbodenheizung", "FUBs/Heizkreise/FBH_ein.webp", 640 / 400],
    ],
    fwm: [
      ["Frischwassermodul", "FUBs/FWM/FWM.webp", 1080 / 860],
      ["FWM Brauchwasser", "FUBs/FWM/FWM_Brauchwasser.webp", 1080 / 860],
    ],
  };
  // visible bounds of each icon (fractions of the image), from the PNG alpha
  const BBOX = {
    "Austragungen_Befuellungen/Pellets_Umschalteinheit/3fach.webp": [0.000,0.060,1.000,0.950],
    "Austragungen_Befuellungen/Pellets_Umschalteinheit/4fach.webp": [0.000,0.060,1.000,0.950],
    "Austragungen_Befuellungen/Pellets_Umschalteinheit/8fach.webp": [0.000,0.060,1.000,0.950],
    "Austragungen_Befuellungen/Hack_Austragung/Schnecke.webp": [0.007,0.023,0.980,0.993],
    "Austragungen_Befuellungen/Ruehrer/Ruehrer.webp": [0.000,0.080,1.000,0.910],
    "Austragungen_Befuellungen/Pendelschnecke/Grundbild_1er.webp": [0.150,0.160,0.850,0.847],
    "Austragungen_Befuellungen/Pendelschnecke/Grundbild_2er.webp": [0.150,0.160,0.850,0.847],
    "Austragungen_Befuellungen/Schubboden/Schubboden_1er.webp": [0.000,0.220,1.000,0.843],
    "Austragungen_Befuellungen/Schubboden/Schubboden_2er.webp": [0.000,0.220,1.000,0.843],
    "Austragungen_Befuellungen/Schubboden/Schubboden_3er.webp": [0.000,0.220,1.000,0.843],

    "Austragungen_Befuellungen/Pelletslager/Pelletslager.webp": [0.008,0.011,0.992,0.989],
    "Kessel/Pellets/PU_PC_neu.webp": [0.059,0.057,0.852,0.921],
    "Kessel/Pellets/PU_PC_grau.webp": [0.059,0.057,0.927,0.924],
    "Kessel/Pellets/PEK.webp": [0.068,0.069,0.921,0.91],
    "Kessel/Pellets/ePEK.webp": [0.063,0.06,0.921,0.926],
    "Kessel/ePE/ePE_HW.webp": [0.231,0.079,0.715,0.903],
    "Kessel/ePE/ePE_einblick.webp": [0.231,0.079,0.715,0.903],
    "Kessel/ePE_BW/ePE_BW.webp": [0.095,0.06,0.875,0.925],
    "Kessel/SH/SH_neu.webp": [0.078,0.07,0.736,0.92],
    "Kessel/SH/SH.webp": [0.068,0.07,0.777,0.934],
    "Kessel/TWIN/SH_TWIN_neu.webp": [0.087,0.032,0.876,0.927],
    "Kessel/TWIN/SH_TWIN.webp": [0.087,0.027,0.9,0.952],
    "Kessel/eSH/FUB_eSH_BE-P3.webp": [0.16,0.046,0.772,0.931],
    "Kessel/eSH/FUB_eSH_BE-P4.webp": [0.161,0.045,0.773,0.931],
    "Kessel/eSH_eTWIN/FUB_eSH-eTWIN_BE-P3.webp": [0.024,0.019,0.892,0.958],
    "Kessel/eSH_eTWIN/FUB_eSH-eTWIN_BE-P4.webp": [0.024,0.019,0.892,0.958],
    "Kessel/eTWIN/FUB_eTWIN_BE-P3.webp": [0.019,0.026,0.884,0.964],
    "Kessel/eTWIN/FUB_eTWIN_BE-P4.webp": [0.019,0.025,0.885,0.964],
    "Kessel/eHack/eHack.webp": [0.061,0.092,0.934,0.892],
    "Kessel/Hack/Hack.webp": [0.061,0.069,0.918,0.918],
    "Kessel/HackVR/HackVR_gelb.webp": [0.042,0.046,0.942,0.958],
    "Kessel/HackVR/HackVR_grau.webp": [0.042,0.046,0.941,0.958],
    "FUBs/PufferFlex/Puffer.webp": [0.156,0.071,0.836,0.929],
    "FUBs/PufferFlex/Puffer_Wendel.webp": [0.157,0.073,0.838,0.93],
    "FUBs/PufferFlex/Kombi.webp": [0.103,0.033,0.923,0.933],
    "FUBs/Heizkreise/Radiator_ein.webp": [0.014,0.133,0.967,0.985],
    "FUBs/Heizkreise/Radiator_aus.webp": [0.014,0.133,0.967,0.985],
    "FUBs/Heizkreise/FBH_ein.webp": [0.0,0.18,0.956,0.95],
    "FUBs/Heizkreise/FBH_aus.webp": [0.0,0.18,0.956,0.95],
    "FUBs/FWM/FWM.webp": [0.234,0.131,0.469,0.803],
    "FUBs/FWM/FWM_Brauchwasser.webp": [0.056,0.131,0.913,0.916],
    "FUBs/Warmwasser/WW.webp": [0.139,0.078,0.858,0.906],
    "FUBs/Solar/Solar.webp": [0.09,0.053,0.898,0.894],
    "FUBs/Externe_Waermeanforderung/Externe_Waermeanforderung.webp": [0.013,0.089,0.958,0.909],
    "Austragungen_Befuellungen/Hack_Austragung/Ruehrwerk.webp": [0.045,0.194,0.999,0.867],
    "FUBs/System/System.webp": [0.08,0.068,0.916,0.927],
    "Kessel/Brenner/Waermepumpe_ein.webp": [0.098,0.066,0.902,0.948],
    "Kessel/Brenner/Waermepumpe_aus.webp": [0.098,0.066,0.902,0.948],
    "Kessel/Brenner/Brenner_ein.webp": [0.072,0.066,0.928,0.957],
    "Kessel/Brenner/Brenner_aus.webp": [0.072,0.066,0.928,0.957],
    "Kessel/Brenner/Biomasse_ein.webp": [0.046,0.066,0.946,0.961],
    "Kessel/Brenner/Biomasse_aus.webp": [0.046,0.066,0.946,0.961],
  };
  // pipe connections inside the icon: [x, y, dir] as image fractions; dir "h" leaves sideways,
  // "v" downwards, "u" straight up (behind the image) to the return line
  const ANCHORS = {
    "FUBs/Heizkreise/Radiator_ein.webp": { in: [0.014, 0.239, "h"], out: [0.141, 0.985, "v"] },
    "FUBs/Heizkreise/Radiator_aus.webp": { in: [0.014, 0.239, "h"], out: [0.141, 0.985, "v"] },
    "FUBs/Heizkreise/FBH_ein.webp": { in: [0.0, 0.72, "h"], out: [0.805, 0.44, "u"] },
    "FUBs/Heizkreise/FBH_aus.webp": { in: [0.0, 0.72, "h"], out: [0.805, 0.44, "u"] },
    "FUBs/Externe_Waermeanforderung/Externe_Waermeanforderung.webp": { in: [0.03, 0.184, "h"], out: [0.013, 0.827, "h"] },
    "FUBs/FWM/FWM_Brauchwasser.webp": { in: [0.07, 0.719, "h"], out: [0.056, 0.207, "h"] },
  };
  // tank body inside images with parts beside it (x fractions): sensors sit on it, pipes leave it
  const BODY = {
    "FUBs/PufferFlex/Kombi.webp": [0.08, 0.62],
  };
  // pellet hose entry per boiler image (fraction of the image): first solid pixel from the left
  const FEED = {
    "Kessel/Pellets/PU_PC_neu.webp": [0.056, 0.298],
    "Kessel/Pellets/PU_PC_grau.webp": [0.056, 0.299],
    "Kessel/Pellets/PEK.webp": [0.065, 0.303],
    "Kessel/Pellets/ePEK.webp": [0.062, 0.303],
    "Kessel/ePE/ePE_HW.webp": [0.257, 0.308],
    "Kessel/ePE/ePE_einblick.webp": [0.257, 0.308],
    "Kessel/ePE_BW/ePE_BW.webp": [0.136, 0.301],
    "Kessel/SH/SH_neu.webp": [0.077, 0.307],
    "Kessel/SH/SH.webp": [0.086, 0.311],
    "Kessel/TWIN/SH_TWIN_neu.webp": [0.086, 0.282],
    "Kessel/TWIN/SH_TWIN.webp": [0.086, 0.285],
    "Kessel/eSH/FUB_eSH_BE-P3.webp": [0.159, 0.293],
    "Kessel/eSH/FUB_eSH_BE-P4.webp": [0.159, 0.293],
    "Kessel/eSH_eTWIN/FUB_eSH-eTWIN_BE-P3.webp": [0.020, 0.281],
    "Kessel/eSH_eTWIN/FUB_eSH-eTWIN_BE-P4.webp": [0.020, 0.281],
    "Kessel/eTWIN/FUB_eTWIN_BE-P3.webp": [0.018, 0.284],
    "Kessel/eTWIN/FUB_eTWIN_BE-P4.webp": [0.018, 0.284],
    "Kessel/eHack/eHack.webp": [0.427, 0.315],
    "Kessel/Hack/Hack.webp": [0.424, 0.306],
    "Kessel/HackVR/HackVR_gelb.webp": [0.211, 0.300],
    "Kessel/HackVR/HackVR_grau.webp": [0.211, 0.300],
  };
  // hose stubs on the boiler roof (image fractions): [suction x, return-air x, stub top y];
  // the stub nearer to the store takes the suction hose
  const STUBS = {
    "Kessel/Pellets/PU_PC_neu.webp": [0.128, 0.190, 0.069],
    "Kessel/Pellets/PU_PC_grau.webp": [0.128, 0.190, 0.069],
    "Kessel/ePE/ePE_HW.webp": [0.305, 0.367, 0.078],
    "Kessel/ePE/ePE_einblick.webp": [0.305, 0.367, 0.078],
    "Kessel/ePE_BW/ePE_BW.webp": [0.214, 0.313, 0.059],
  };
  // boilers without pellet hoses: log and wood chip boilers (the chip store keeps its auger)
  const NO_HOSE = /^Kessel\/(SH|eSH|Hack|eHack|HackVR)\//;
  // free space between pellet store and boiler for the hoses
  const HOSE_GAP = 64;
  // visible height of the device on the 1600px canvas, per block type
  const TARGET_H = {
    silo: 220, chip_store: 200, boiler: 300, buffer: 330, heating_circuit: 140, fwm: 170,
    dhw: 290, solar: 220, unknown: 150, external_demand: 150, external_heat: 150,
  };
  // default icon per ETA object id where the type alone is ambiguous
  const DEFAULT_BY_OBJECT = {
    "10561": ["Kessel/Hack/Hack.webp", 1],
    "10261": ["Kessel/Pellets/PEK.webp", 840 / 1000],
    // SH-TWIN: log wood boiler (10391) with pellet unit (10401)
    "10391": ["Kessel/SH/SH_neu.webp", 780 / 980],
    "10401": ["Kessel/TWIN/SH_TWIN_neu.webp", 1020 / 920],
    // other heat source controlled by the ETA (oil / gas burner, heat pump, ...)
    "10281": ["Kessel/Brenner/Brenner_ein.webp", 540 / 440],
  };
  // heating circuit pictures with an "off" variant (…_aus.webp)
  const HK_OFF = /^FUBs\/Heizkreise\/(Radiator|FBH)_ein\.webp$/;
  // SH-TWIN: the pellet unit (key) is built onto the wood boiler (value). ETA controls them as two
  // function blocks, but it is one boiler with one water side: the plant view draws one block
  // with the SH-TWIN icon, the control tab keeps both (each has its own on/off).
  const TWIN_PAIRS = { "10401": "10391" };
  const mergeTwins = (list) => {
    const out = [...list];
    out.filter((b) => b.type === "boiler" && TWIN_PAIRS[b.object]).forEach((b) => {
      const partner = out.find((x) => x.type === "boiler" && x.object === TWIN_PAIRS[b.object]);
      if (!partner) return;
      const merged = { ...b, roles: { ...partner.roles, ...b.roles }, entities: [...b.entities, ...partner.entities], partner };
      out.splice(out.indexOf(b), 1, merged);
      out.splice(out.indexOf(partner), 1);
    });
    return out;
  };
  // parts beside the heat flow (particle separator, condensing heat exchanger): control tab only
  const SIDE_ICONS = {
    particle_separator: { off: "Kessel/EP_Abscheider/EP.webp", on: "Kessel/EP_Abscheider/EP_aktiv.webp" },
    condenser: { off: "Kessel/Brennwert_WT/Brennwert_WT.webp", on: "Kessel/Brennwert_WT/Brennwert_WT.webp" },
  };
  const LABELS = {
    de: {
      silo: "Silo", chip_store: "Hackgutlager", boiler: "Kessel", buffer: "Puffer", heating_circuit: "Heizkreis",
      fwm: "Frischwasser", dhw: "Warmwasser", solar: "Solar", unknown: "Modul", particle_separator: "Partikelabscheider", condenser: "Brennwertwärmetauscher",
      external_demand: "Ext. Anforderung", external_heat: "Fremdwärme",
      no_blocks: "Keine Anlagenteile erkannt. Wähle in den Integrationsoptionen die Entitäten von Kessel, Heizkreis usw. aus oder melde deine Anlage über das Zahnrad.", outside: "Außen", tab_plant: "Anlage", tab_ctl: "Bedienung",
      heat: "Heizen", lower: "Absenken", auto: "Zeitautomatik", ask_off: "wirklich ausschalten?",
      no_ctl: "Keine Schalter gefunden. In den Optionen der Integration die Schalter (z. B. Ein/Aus Taste) auswählen.",
      times: "Heizzeiten", days: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"], from: "von", to: "bis",
      apply: "Übernehmen für", only_day: "nur diesen Tag", workdays: "Mo–Fr", weekend: "Sa–So", all_days: "alle Tage",
      save: "Speichern", cancel: "Abbrechen", saving: "Wird geschrieben …", ro: "Nur lesbar. Bearbeiten ab ETA-API 1.2: Einstellungen → Geräte & Dienste → ETA Heating → Konfigurieren → „Ausgewählte Entitäten aktualisieren“ → Heizzeiten unter „Schreibbare Sensoren“ auswählen.",
      bad_slot: "Ungültiges Zeitfenster: Beginn muss vor dem Ende liegen.",
      ash: "Aschebox", hopper: "Tagesbehälter", pellets: "Pellets", wood: "Holz", empty_now: "jetzt leeren", d_unit: "Tage",
      fc_seasonal: "Prognose aus Vorjahr", fc_average: "Prognose aus Ø 14 Tagen",
      in_days: (n) => `leeren in ca. ${n} ${n === 1 ? "Tag" : "Tagen"}`,
      in_weeks: (n) => `leeren in ca. ${n} Wochen`, in_months: (n) => `leeren in ca. ${n} Monaten`,
      not_selected: "nicht ausgewählt",
      hint_selected: "Dieser Wert ist am Terminal vorhanden, aber in der Integration nicht ausgewählt. Einstellungen → Geräte & Dienste → ETA Heating → Konfigurieren → „Ausgewählte Entitäten aktualisieren“ → Wert auswählen. Soll er nicht angezeigt werden: Zahnrad → Werte manuell zuordnen → „nicht anzeigen“.",
    },
    en: {
      silo: "Storage", chip_store: "Chip store", boiler: "Boiler", buffer: "Buffer", heating_circuit: "Heating circuit",
      fwm: "Fresh water", dhw: "Hot water", solar: "Solar", unknown: "Module", particle_separator: "Particle separator", condenser: "Condensing heat exchanger",
      external_demand: "Ext. demand", external_heat: "External heat",
      no_blocks: "No plant parts detected. Select the boiler, heating circuit, ... entities in the integration options or report your plant via the gear.", outside: "Outside", tab_plant: "Plant", tab_ctl: "Control",
      heat: "Heat", lower: "Setback", auto: "Time program", ask_off: "really switch off?",
      no_ctl: "No switches found. Select the switches (e.g. On/Off button) in the integration options.",
      times: "Heating times", days: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], from: "from", to: "to",
      apply: "Apply to", only_day: "this day only", workdays: "Mon–Fri", weekend: "Sat–Sun", all_days: "all days",
      save: "Save", cancel: "Cancel", saving: "Writing …", ro: "Read only. Editing from ETA API 1.2: Settings → Devices & services → ETA Heating → Configure → \u201cUpdate selected entities\u201d → select the heating times under \u201cPossible writable sensors\u201d.",
      bad_slot: "Invalid time slot: start must be before end.",
      ash: "Ash box", hopper: "Hopper", pellets: "Pellets", wood: "Wood", empty_now: "empty now", d_unit: "days",
      fc_seasonal: "forecast from last year", fc_average: "forecast from 14-day average",
      in_days: (n) => `empty in approx. ${n} ${n === 1 ? "day" : "days"}`,
      in_weeks: (n) => `empty in approx. ${n} weeks`, in_months: (n) => `empty in approx. ${n} months`,
      not_selected: "not selected",
      hint_selected: "This value exists on the terminal but is not selected in the integration. Settings → Devices & services → ETA Heating → Configure → \u201cUpdate selected entities\u201d → select the value. To hide it: gear → Assign values manually → \u201cdo not show\u201d.",
    },
  };
  // value roles shown above the icon
  const TOP_VALUES = {
    silo: ["stock"],
    chip_store: ["discharge"],
    boiler: ["temperature", "hopper", "pressure", "oxygen"],
    buffer: ["charge"],
    heating_circuit: ["flow"],
    fwm: ["hot_water", "flow", "primary_flow"],
    dhw: ["temperature"],
    solar: ["collector"],
    external_heat: ["temperature"],
  };
  const IDLE = ["bereit", "aus", "ready", "off", "standby", "abgeschaltet", "ausgeschaltet", "unavailable", "unknown"];
  const ON = ["ein", "an", "on", "true", "läuft", "running"];
  const CONSUMERS = ["heating_circuit", "external_demand", "fwm", "dhw", "unknown"];
  // other heat sources (heat pump, oil / gas burner, ...) feed the buffer like a boiler:
  // parts of type "Fremdwärme", the ETA burner object 10281 and parts shown with such an image
  const HEAT_IMG = /^Kessel\/Brenner\//;
  // height of the lines at a heat source (image fraction): the heat pump's outdoor unit sits low
  const HEAT_PIPE_Y = { "Kessel/Brenner/Waermepumpe_ein.webp": 0.56, "Kessel/Brenner/Waermepumpe_aus.webp": 0.56 };
  const isHeat = (b, icons) => {
    const pick = (icons || {})[b.id];
    if (pick) return HEAT_IMG.test(pick);
    return b.type === "external_heat" || b.object === "10281";
  };
  // heat sources not placed by hand sit right before the buffer (without buffer: right after
  // the last boiler), so they connect like a boiler and not across the consumers
  const placeHeat = (list, order, icons) => {
    const free = list.filter((b) => !order.includes(b.id) && isHeat(b, icons));
    free.forEach((b) => {
      list.splice(list.indexOf(b), 1);
      const buf = list.findIndex((x) => x.type === "buffer");
      const boil = list.map((x) => x.type).lastIndexOf("boiler");
      const at = buf >= 0 ? buf : boil >= 0 ? boil + 1 : list.length;
      list.splice(Math.min(at, list.length), 0, b);
    });
    return list;
  };

  // roles a user can assign by hand in the editor, per block type: [role, German label, English label, kind]
  const EDIT_ROLES = {
    plant: [["outside", "Außentemperatur", "Outside temperature", "temp"]],
    boiler: [["temperature", "Kesseltemperatur", "Boiler temperature", "temp"], ["pressure", "Druck", "Pressure", "bar"],
      ["hopper", "Vorratsbehälter", "Hopper", "level"], ["oxygen", "Restsauerstoff", "Residual oxygen", "level"],
      ["status", "Status", "Status", "text"],
      ["pump", "Pumpe", "Pump", "onoff"], ["switch", "Ein/Aus-Taste", "On/off button", "switch"]],
    silo: [["stock", "Vorrat", "Stock", "level"], ["status", "Status", "Status", "text"], ["auger", "Förderung", "Conveyor", "onoff"]],
    chip_store: [["auger", "Förderung", "Conveyor", "onoff"], ["discharge", "Austragung", "Discharge", "onoff"]],
    buffer: [["top", "Oben", "Top", "temp"], ["middle", "Mitte", "Middle", "temp"], ["bottom", "Unten", "Bottom", "temp"],
      ["charge", "Ladezustand", "Charge", "level"], ["status", "Status", "Status", "text"]],
    heating_circuit: [["flow", "Vorlauftemperatur", "Flow temperature", "temp"], ["status", "Status", "Status", "text"],
      ["pump", "Pumpe", "Pump", "onoff"], ["switch", "Ein/Aus-Taste", "On/off button", "switch"],
      ["heat", "Taste Heizen", "Heat button", "switch"], ["lower", "Taste Absenken", "Setback button", "switch"],
      ["auto", "Taste Zeitautomatik", "Time program button", "switch"]],
    dhw: [["temperature", "Warmwassertemperatur", "Hot water temperature", "temp"], ["status", "Status", "Status", "text"],
      ["pump", "Pumpe", "Pump", "onoff"]],
    solar: [["collector", "Kollektor", "Collector", "temp"], ["storage_top", "Speicher oben", "Storage top", "temp"],
      ["status", "Status", "Status", "text"], ["pump", "Pumpe", "Pump", "onoff"]],
    external_heat: [["temperature", "Temperatur", "Temperature", "temp"], ["storage", "Speicher", "Storage", "temp"],
      ["pump", "Pumpe", "Pump", "onoff"], ["status", "Status", "Status", "text"]],
    fwm: [["hot_water", "Warmwasser", "Hot water", "temp"], ["flow", "Durchfluss", "Flow rate", "flow"],
      ["primary_flow", "Vorlauf primär", "Primary flow", "temp"],
      ["primary_return", "Rücklauf primär", "Primary return", "temp"], ["status", "Status", "Status", "text"],
      ["pump", "Pumpe", "Pump", "onoff"], ["switch", "Ein/Aus-Taste", "On/off button", "switch"]],
    external_demand: [["status", "Status", "Status", "text"]],
    particle_separator: [["status", "Status", "Status", "text"]],
    condenser: [["status", "Status", "Status", "text"], ["return", "Rücklauf", "Return", "temp"]],
    unknown: [["temperature", "Temperatur", "Temperature", "temp"], ["status", "Status", "Status", "text"]],
  };
  // block types a user can add by hand
  const ADD_TYPES = ["boiler", "silo", "buffer", "heating_circuit", "dhw", "solar", "fwm", "external_heat"];

  // manual settings of the editor on top of the detected topology:
  // roles {block: {role: entity | "-" (none)}}, names {block: text}, hidden [block], extra [{id, type}]
  const applyConfig = (topo, cfg) => {
    if (!topo) return topo;
    const ov = cfg.roles || {};
    const names = cfg.names || {};
    const hidden = new Set(cfg.hidden || []);
    const blocks = topo.blocks.map((b) => ({ ...b, roles: { ...b.roles }, entities: [...b.entities], unselected: { ...(b.unselected || {}) } }));
    (cfg.extra || []).forEach((x) => blocks.push({ id: x.id, type: x.type, object: "", name: null, roles: {}, entities: [], manual: true }));
    blocks.forEach((b) => {
      const o = ov[b.id] || {};
      Object.entries(o).forEach(([role, e]) => {
        if (b.unselected && e) delete b.unselected[role]; // picked or hidden by hand: no hint
        if (e === "-") delete b.roles[role];
        else if (e) {
          b.roles[role] = e;
          if (!b.entities.includes(e)) b.entities.push(e);
          (b.picked = b.picked || []).push(role);
        }
      });
      // a hand-picked top / middle / bottom sensor replaces the numbered buffer sensors
      if (b.type === "buffer" && ["top", "middle", "bottom"].some((r) => r in o)) {
        Object.keys(b.roles).filter((r) => /^sensor_\d+$/.test(r)).forEach((r) => delete b.roles[r]);
      }
      if (names[b.id]) b.label = names[b.id];
    });
    const plant = { ...(topo.plant || {}) };
    Object.entries(ov.plant || {}).forEach(([role, e]) => { if (e === "-") delete plant[role]; else if (e) plant[role] = e; });
    // a part added by hand whose values all belong to a detected part of the same type is a
    // duplicate (the detection learned it later, e.g. after an update): leave it out
    const dup = (b) => {
      if (!b.manual) return false;
      const mine = Object.values(b.roles).filter((e) => e && e !== "-");
      return mine.length > 0 && blocks.some((x) => !x.manual && x.type === b.type
        && mine.every((e) => (topo.blocks.find((t) => t.id === x.id) || { entities: [] }).entities.includes(e)));
    };
    const dups = new Set(blocks.filter(dup).map((b) => b.id));
    // order picked by hand (like on the ETA terminal); parts not in the list keep their place at the end
    const order = cfg.order || [];
    const pos = (b, i) => { const k = order.indexOf(b.id); return k < 0 ? order.length + i : k; };
    const sorted = blocks.map((b, i) => [pos(b, i), b]).sort((x, y) => x[0] - y[0]).map(([, b]) => b);
    placeHeat(sorted, order, cfg.icons);
    return { ...topo, plant, blocks: sorted.filter((b) => !hidden.has(b.id) && !dups.has(b.id)) };
  };

  // pellet hopper at the boiler: ETA reports its content in kg but no capacity. The boiler
  // fills it up at least once a day, so the highest value of the last 48 h counts as 100 %;
  // HOPPER_KG only until history exists.
  const HOPPER_KG = 30;
  const HOPPER_HOURS = 48;
  const hopSvg = (size) => `<svg viewBox="0 0 40 40" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M8 7h24v13l-7 9v5H15v-5l-7-9z"/><circle cx="15" cy="16" r="2.2" fill="currentColor" stroke="none"/><circle cx="21" cy="14" r="2.2" fill="currentColor" stroke="none"/><circle cx="26" cy="17" r="2.2" fill="currentColor" stroke="none"/><circle cx="19" cy="20" r="2.2" fill="currentColor" stroke="none"/></svg>`;

  // ash box symbol (plant view and control tab)
  const ashSvg = (size) => `<svg viewBox="0 0 40 40" width="${size}" height="${size}" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M9 13h22l-2 21H11z"/><path d="M6 13h28M16 9h8"/><path d="M12 25h16" stroke-width="5" opacity=".55"/></svg>`;

  const css = `
  :host{display:block}
  ha-card{display:block;overflow:hidden;background:#111;border:2px solid #f5b800;border-radius:14px}
  .box{position:relative;width:100%}
  .cv{position:absolute;left:0;top:0;width:${W}px;height:${H}px;transform-origin:0 0;
      font-family:"Helvetica Neue",Arial,sans-serif;color:#f2f2f2;
      background:repeating-linear-gradient(90deg,rgba(255,255,255,.012) 0 2px,rgba(0,0,0,.02) 2px 4px),
        linear-gradient(180deg,#262626,#181818 40%,#121212)}
  .hdr{position:absolute;left:0;right:0;top:0;height:64px;display:flex;align-items:center;gap:24px;padding:0 28px;
       background:linear-gradient(#2c2c2c,#1a1a1a);border-bottom:3px solid #f5b800}
  .hdr h1{font-size:28px;font-weight:600;margin:0;flex:1;display:flex;align-items:center;gap:14px}
  .beta{font-size:15px;font-weight:700;letter-spacing:1px;color:#1a1a1a;background:#ffc400;border-radius:6px;padding:3px 8px}
  .hdr .m{font-size:22px;color:#ddd}.hdr .m b{color:#ffc400;font-weight:500}
  .floor{position:absolute;left:0;right:0;top:${FLOOR - 20}px;bottom:0;
    background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(0,0,0,0) 30%);border-top:1px solid rgba(255,255,255,.06)}
  .g{position:absolute;left:0;top:0}
  .p{position:absolute;border-radius:5px;overflow:hidden}
  .p.vl{background:#9c1f17;z-index:3}.p.rl{background:#1d4f9e;z-index:1}
  .gap{position:absolute;z-index:2;background:#141414;pointer-events:none}
  .ashrow{display:flex;align-items:center;gap:8px;margin:0 auto 18px;cursor:pointer;color:#ffc400;font-size:16px}
  .ashrow.warn{color:#ff8c00}.ashrow.full{color:#e53935}.ashrow .pc{color:#aaa;min-width:40px}
  .ashrow.warn .pc,.ashrow.full .pc{color:inherit}
  .rows{display:flex;flex-direction:column;align-items:flex-start;gap:8px;margin:0 auto 18px}
  .rows .ashrow{margin:0}
  .ashbar{width:120px;height:8px;border-radius:4px;background:#3a3a3a;overflow:hidden}
  .ashbar i,.ash .bar i{display:block;height:100%;width:0;background:#ffc400;transition:width .4s}
  .ashrow.warn i,.ash.warn .bar i{background:#ff8c00}.ashrow.full i,.ash.full .bar i{background:#e53935}
  .ash{display:flex;align-items:center;gap:12px;margin-top:16px;cursor:pointer;font-size:18px;color:#ddd}
  .ash svg{flex:none;color:#ffc400}.ash.warn svg{color:#ff8c00}.ash.full svg{color:#e53935}
  .ash .col{flex:1;min-width:0}.ash .fc{margin-top:6px;font-size:14px;color:#888}
  .ash .bar{height:12px;margin-top:8px;border-radius:6px;background:#3a3a3a;overflow:hidden}
  .ash .tx{min-width:0;white-space:nowrap}.ash .tx b{font-weight:600;color:#fff}.ash .tx span{color:#aaa;margin-left:8px}
  .p.pe{background:#4a4a4a;box-shadow:inset 0 0 0 1px rgba(255,255,255,.12)}
  .p.air{background:#3f4850;box-shadow:inset 0 0 0 1px rgba(255,255,255,.12)}
  .off .p{opacity:.65}
  /* moving dashes: one path per pipe run, so they follow the bends */
  .fl{position:absolute;left:0;top:0;width:1px;height:1px;overflow:visible;pointer-events:none}
  .fl.vl{z-index:3}.fl.rl{z-index:1}
  .fl path{fill:none;stroke-width:4;stroke-dasharray:7 17;stroke-linejoin:round}
  .fl.vl path{stroke:#ff8a7a}.fl.rl path{stroke:#7fb2ff}
  .fl.pe path,.fl.air path{stroke-linecap:round;stroke-dasharray:0 8}
  .fl.pe path{stroke:#ffc400;stroke-width:4.4}.fl.air path{stroke:#9fd8ff;stroke-width:3.6}
  .on .fl path{animation:fd .9s linear infinite}.on .fl.pe path,.on .fl.air path{animation-duration:.6s}
  .off .fl{display:none}
  .band{position:absolute;height:16px;border-radius:4px;overflow:hidden;background:#3a3a3a;box-shadow:inset 0 0 0 1px rgba(255,255,255,.12)}
  .band i{position:absolute;left:-20px;right:-20px;top:0;bottom:0;will-change:transform;
    background:repeating-linear-gradient(45deg,#ffc400 0 9px,#2a2400 9px 14px)}
  .on .band i{animation:mb 1.2s linear infinite}.off .band i{display:none}
  @keyframes fd{from{stroke-dashoffset:var(--o,0px)}to{stroke-dashoffset:calc(var(--o,0px) - 24px)}}
  @keyframes mb{to{transform:translateX(19.8px)}}
  .blk{position:absolute;z-index:4;top:64px;display:flex;flex-direction:column;align-items:center;cursor:pointer}
  .vals{display:flex;align-items:flex-end;gap:8px;padding-bottom:14px}
  .pill.na{display:none}
  .pill.ghost{border:1px dashed #888;background:transparent;box-shadow:none;color:#aaa}
  .t-silo .vals,.t-chip_store .vals{padding-bottom:34px}
  .t-silo .vals{flex-direction:column;align-items:center;gap:6px}
  .t-boiler .vals,.t-fwm .vals{flex-wrap:wrap;justify-content:center;row-gap:8px;width:100%}
  .t-fwm .stack{max-width:100%}
  .stack{height:${FLOOR - 64}px;display:flex;flex-direction:column;justify-content:flex-end;align-items:center}
  .icon{display:flex;align-items:flex-end;position:relative}
  .icon img{display:block;position:relative}
  .shadow{position:absolute;left:8%;right:8%;bottom:-12px;height:26px;border-radius:50%;background:radial-gradient(ellipse at center,rgba(0,0,0,.7),transparent 70%)}
  .cv{contain:layout paint}
  .name{font-size:22px;font-weight:600;margin-top:40px;text-align:center;max-width:300px}
  .chip{margin-top:8px;padding:6px 16px;border-radius:9px;font-size:19px;font-weight:600;color:#1a1a1a;
        background:linear-gradient(90deg,#ffd31a,#ffc000);max-width:300px;text-align:center}
  .chips{display:flex;flex-direction:column;align-items:center}.chips .chip{font-size:16px;padding:4px 12px;margin-top:6px}
  .chip.idle{background:linear-gradient(90deg,#8a8a8a,#6f6f6f);color:#111}
  .pill{padding:6px 12px;border-radius:10px;background:#1d1d1d;border:1px solid #3b3b3b;
        box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 4px 10px rgba(0,0,0,.5);font-size:26px;font-weight:500;white-space:nowrap}
  .pill u{text-decoration:none;color:#ffc400;font-size:22px;margin-left:3px}
  .tank{position:absolute;left:0;right:0;top:0;bottom:0;display:flex;flex-direction:column;
        justify-content:space-around;align-items:center;padding:18% 0 6%}
  .tank.many .pill{font-size:19px;padding:3px 9px}
  .empty{padding:40px;font-size:24px}
  .pill,.chip,.hdr .m{cursor:pointer}
  .tabs{display:flex;gap:6px}
  .tabs button{font:inherit;font-size:21px;font-weight:600;color:#ddd;background:#1b1b1b;border:1px solid #444;
    border-radius:9px;padding:7px 20px;cursor:pointer}
  .tabs button.act{color:#1a1a1a;background:linear-gradient(90deg,#ffd31a,#ffc000);border-color:#ffc000}
  .pg{position:absolute;left:0;top:0;right:0;bottom:0}
  .pg.hide{display:none}
  .tiles{position:absolute;left:0;right:0;top:64px;bottom:0;padding:30px 28px;display:flex;flex-wrap:wrap;
    gap:26px;align-content:flex-start;overflow-y:auto}
  .tile{width:490px;box-sizing:border-box;background:#1b1b1b;border:1px solid #3b3b3b;border-radius:14px;padding:18px 20px;
    box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 6px 16px rgba(0,0,0,.5)}
  .th{display:flex;align-items:center;gap:16px}
  .th img{height:96px;width:110px;object-fit:contain}
  .th .tx{flex:1;min-width:0}
  .tn{font-size:24px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .th .chip{display:inline-block;margin-top:8px;font-size:17px;padding:4px 12px}
  .tg{display:flex;align-items:center;gap:8px;font-size:22px;font-weight:700;color:#bbb;cursor:pointer;user-select:none}
  .tg b{width:76px;height:36px;border-radius:18px;background:#555;position:relative;transition:background .2s}
  .tg b:after{content:"";position:absolute;top:4px;left:4px;width:28px;height:28px;border-radius:50%;
    background:linear-gradient(#eee,#aaa);transition:left .2s}
  .tg.on b{background:linear-gradient(90deg,#ffd31a,#ffc000)}.tg.on b:after{left:44px}
  .modes{display:flex;gap:12px;margin-top:18px}
  .md{flex:1;font:inherit;font-size:18px;font-weight:600;color:#ddd;background:#232323;border:1px solid #444;border-radius:12px;
    padding:12px 6px;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:6px}
  .md i{font-style:normal;line-height:0}
  .md.act{color:#ffc400;border-color:#ffc400;background:#2b2610}
  .tile .vrow{display:flex;gap:10px;margin-top:14px}
  .tile .pill{font-size:22px}
  .busy{opacity:.5;pointer-events:none}
  .ts{position:relative;margin-top:18px;height:46px;cursor:pointer}
  .ts .bar{position:absolute;left:0;right:0;top:0;height:22px;border-radius:6px;background:#3a3a3a;overflow:hidden;
    box-shadow:inset 0 1px 3px rgba(0,0,0,.6)}
  .ts .w{position:absolute;top:0;bottom:0;background:linear-gradient(#ffd31a,#ffb800)}
  .ts .bar::after{content:"";position:absolute;inset:0;pointer-events:none;
    background:repeating-linear-gradient(90deg,rgba(255,255,255,.8) 0 1px,transparent 1px 25%) left bottom/100% 11px no-repeat,
      repeating-linear-gradient(90deg,rgba(255,255,255,.55) 0 1px,transparent 1px calc(100% / 24)) left bottom/100% 6px no-repeat}
  .ts .now{z-index:1;position:absolute;top:-6px;height:34px;width:3px;margin-left:-1px;background:#fff;box-shadow:0 0 4px #000}
  .ts .ax{position:absolute;left:0;right:0;top:26px;font-size:14px;color:#aaa}
  .ts .ax span{position:absolute;transform:translateX(-50%)}
  .ts .ax span:first-child{transform:none}.ts .ax span:last-child{transform:translateX(-100%)}
  .dlg{position:fixed;inset:0;z-index:10;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;
    font-family:Roboto,Arial,sans-serif}
  .dlg .in{background:#1d1d1d;color:#eee;border:1px solid #ffc400;border-radius:12px;padding:18px 20px;width:min(440px,92vw);
    max-height:90vh;overflow:auto;box-sizing:border-box}
  .dlg h2{margin:0 0 12px;font-size:19px;color:#ffc400}
  .dlg .dy{display:flex;gap:4px;margin-bottom:14px}
  .dlg .dy button{flex:1;padding:7px 0;border-radius:7px;border:1px solid #444;background:#2a2a2a;color:#ddd;cursor:pointer;font-size:14px}
  .dlg .dy button.act{background:#ffc400;color:#1a1a1a;border-color:#ffc400;font-weight:700}
  .dlg .sl{display:flex;align-items:center;gap:8px;margin:8px 0;font-size:15px}
  .dlg input,.dlg select{background:#2a2a2a;color:#eee;border:1px solid #555;border-radius:6px;padding:6px;font-size:15px;color-scheme:dark}
  .dlg input[type=number]{width:64px}
  .dlg .ap{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:14px;font-size:15px}
  .dlg .bt{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}
  .dlg .bt button{padding:8px 16px;border-radius:8px;border:1px solid #555;background:#2a2a2a;color:#eee;cursor:pointer;font-size:15px}
  .dlg .bt .ok{background:#ffc400;color:#1a1a1a;border-color:#ffc400;font-weight:700}
  .dlg .msg{margin-top:10px;font-size:13px;color:#ffb3b3}.dlg .hint{font-size:13px;color:#aaa;margin-top:10px}`;

  // icons ship with the integration (served by card.py under /eta_webservices_static)
  const ICON_BASE = "/eta_webservices_static/icons";
  const iconSrc = (file) => `${ICON_BASE}/${file}?r=${ICON_REV}`;
  // icon choices saved by earlier versions used .png names
  const webp = (file) => (file ? String(file).replace(/\.png$/, ".webp") : file);

  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  class EtaPlantCard extends HTMLElement {
    setConfig(config) {
      const prevEntry = this._config && this._config.entry;
      this._config = { ...config };
      if (this._raw && prevEntry === this._config.entry && this._hass) {
        this._topo = applyConfig(this._raw, this._config);
        this._build(); // keep the known plant, only re-render
      } else {
        this._topo = null;
        this._raw = null;
        this._built = false;
      }
    }

    static getConfigElement() {
      return document.createElement("eta-plant-card-editor");
    }

    static getStubConfig() {
      return {};
    }

    getCardSize() {
      return 8;
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._topo && !this._loading) this._load();
      if (this._built && this._builtLang !== this._lang()) this._build(); // HA language changed
      else if (this._built) this._update();
    }

    async _load() {
      this._loading = true;
      try {
        const all = await this._hass.callWS({ type: "eta_webservices/topology" });
        const want = this._config.entry;
        this._raw = (want && all.find((e) => e.entry_id === want || e.title === want)) || all[0] || null;
        this._topo = applyConfig(this._raw, this._config);
      } catch (err) {
        this._topo = null;
        this._error = String(err && err.message ? err.message : err);
      }
      this._loading = false;
      this._build();
    }

    _lang() {
      const lang = this._config.language || (this._hass.locale && this._hass.locale.language) || this._hass.language || "en";
      return lang.startsWith("de") ? "de" : "en";
    }

    _t(key) {
      const lang = this._lang();
      return (LABELS[lang.startsWith("de") ? "de" : "en"] || LABELS.en)[key] || key;
    }

    _build() {
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      const root = this.shadowRoot;
      root.innerHTML = `<style>${css}</style><ha-card><div class="box"><div class="cv"></div></div></ha-card>`;
      const cv = root.querySelector(".cv");
      if (!this._topo) {
        cv.innerHTML = `<div class="empty">ETA: ${this._error || "keine Anlage gefunden"}</div>`;
        this._fit();
        return;
      }
      const blocks = mergeTwins(this._topo.blocks.filter((b) => ICONS[b.type] || b.type === "unknown"));
      // boilers with their own discharge (wood chips) get a virtual store in front
      if (!blocks.some((b) => b.type === "silo")) {
        const bi = blocks.findIndex((b) => b.type === "boiler" && b.roles.auger);
        if (bi >= 0) {
          const bo = blocks[bi];
          const roles = { auger: bo.roles.auger };
          if (bo.roles.discharge) roles.discharge = bo.roles.discharge;
          blocks.splice(bi, 0, { id: `${bo.id}/store`, type: "chip_store", object: "", name: null, roles, entities: [] });
        }
      }
      this._blocks = blocks;
      const n = Math.max(blocks.length, 1);
      const colW = W / n;
      const scale = Math.min(1, colW / 330);
      this._geo = blocks.map((b, i) => {
        let [file, iw, aspect] = ICONS[b.type] || ICONS.unknown;
        if (DEFAULT_BY_OBJECT[b.object]) [file, aspect] = DEFAULT_BY_OBJECT[b.object];
        const pick = webp((this._config.icons || {})[b.id]);
        const choice = pick && (ICON_CHOICES[b.type] || []).find((c) => c[1] === pick);
        if (pick) { file = pick; aspect = choice ? choice[2] : aspect; }
        const bx = BBOX[file] || [0, 0, 1, 1];
        // same visible device height per type, independent of the image margins
        // other heat sources are drawn like a small boiler, not like a module
        const th = /^Kessel\/Brenner\//.test(file) ? 230 : TARGET_H[b.type] || TARGET_H.unknown;
        let h = th / (bx[3] - bx[1]);
        let w = h * aspect;
        const maxVisW = colW * 0.85;
        const visW = (bx[2] - bx[0]) * w;
        if (visW > maxVisW) { w *= maxVisW / visW; h *= maxVisW / visW; }
        const cx = colW * (i + 0.5);
        // the tank body, not the whole image, is centred in its column, as far as the
        // column has room: parts beside it (tap) must leave space for the next pipes
        const body = BODY[file] || [bx[0], bx[2]];
        const room = Math.max(0, colW / 2 - 40 - (bx[2] - 0.5) * w);
        const dx = BODY[file] ? Math.min((0.5 - (body[0] + body[1]) / 2) * w, room) : 0;
        const x0 = cx - w / 2 + dx;
        const sink = (1 - bx[3]) * h; // transparent margin below the device
        const y0 = FLOOR - h + sink;
        return {
          b, file, bx, body, cx, w, h, x0, y0, sink, dx: dx || 0, left: x0 + bx[0] * w, right: x0 + bx[2] * w,
          bodyRight: x0 + body[1] * w,
          shift: BODY[file] ? x0 + (body[0] + body[1]) / 2 * w - cx : 0,
          top: y0 + bx[1] * h, bottom: y0 + bx[3] * h, anchors: ANCHORS[file],
        };
      });
      this._roomForHoses();

      const plant = this._topo.plant || {};
      const firstBoiler = blocks.find((x) => x.type === "boiler");
      let html = `<div class="pg plant"><div class="floor"></div>${this._pipes()}`;
      if (!blocks.length) html += `<div class="empty">${this._t("no_blocks")}</div>`;
      for (const g of this._geo) {
        const b = g.b;
        let shown = (TOP_VALUES[b.type] || []).filter((r) => b.roles[r]).map((r) => b.roles[r]);
        // buffer sensors top to bottom: all numbered sensors if present, else top / middle / bottom
        const numbered = Object.keys(b.roles).filter((r) => /^sensor_\d+$/.test(r)).sort((x, y) => +x.slice(7) - +y.slice(7));
        const inner = numbered.length ? numbered : ["top", "middle", "bottom"].filter((r) => b.roles[r]);
        const hasInner = b.type === "buffer" && inner.length > 0;
        // main value found on the terminal but not selected in the integration: placeholder with a hint
        const main = (TOP_VALUES[b.type] || [])[0];
        const ghost = main && !b.roles[main] && (b.unselected || {})[main] ? main : null;
        if (!shown.length && !hasInner && !ghost) shown = this._autoValues(b); // no known roles: pick measurements
        if (b.type === "silo" && plant.silo_days) shown.push(plant.silo_days); // forecast: pellets last approx. n days
        // narrow columns: fewer value boxes; boilers and fresh water modules keep theirs and wrap into a second row
        shown = shown.slice(0, b.type === "boiler" ? 4 : b.type === "fwm" ? 3 : Math.max(1, Math.floor(colW / 110)));
        const ghostUnit = ((EDIT_ROLES[b.type] || []).find((r) => r[0] === ghost) || [])[3] === "temp" ? " °C" : "";
        const vals = (ghost ? `<div class="pill ghost" data-hint="${esc(this._roleLabel(b.type, ghost))}: ${this._t("not_selected")}">?${ghostUnit}</div>` : "")
          + shown.map((e) => `<div class="pill" data-e="${e}"></div>`).join("");
        const tank = b.type === "buffer"
          ? `<div class="tank${inner.length > 4 ? " many" : ""}" style="left:${g.body[0] * 100}%;right:${(1 - g.body[1]) * 100}%">${inner
              .map((r) => `<div class="pill" data-e="${b.roles[r]}"></div>`).join("")}</div>`
          : "";
        // values, name and status stand over the tank body
        const mv = g.shift ? ` style="transform:translateX(${g.shift}px)"` : "";
        html += `<div class="blk t-${b.type}" data-b="${b.id}" style="left:${g.cx - colW / 2}px;width:${colW}px">
          <div class="stack">${this._boilerRows(b, b === firstBoiler)}<div class="vals"${mv}>${vals}</div>
          <div class="icon" style="margin-bottom:${-g.sink}px${g.dx ? `;transform:translateX(${g.dx}px)` : ""}"><div class="shadow" style="bottom:${g.sink - 12}px"></div><img data-type="${b.type}"${/^Kessel\/Brenner\/.*_ein\.webp$/.test(g.file) ? ` data-onoff="${g.file}"` : ""}${b.type === "heating_circuit" ? ` data-file="${g.file}"` : ""} src="${iconSrc(g.file)}" style="width:${g.w}px">${tank}</div></div>
          <div class="name"${mv}>${this._name(b)}</div>
          ${b.partner && b.partner.roles.status && b.roles.status
            ? `<div class="chips"${mv}><div class="chip" data-chip="${b.roles.status}" data-pre="${this._t("pellets")}"></div><div class="chip" data-chip="${b.partner.roles.status}" data-pre="${this._t("wood")}"></div></div>`
            : b.roles.status ? `<div class="chip" data-chip="${b.roles.status}"${mv}></div>` : ""}
        </div>`;
      }
      const ctl = this._controlHtml();
      const tab = ctl && this._tab === "ctl" ? "ctl" : "plant";
      html += `</div><div class="pg ctl ${tab === "ctl" ? "" : "hide"}">${ctl || ""}</div>`;
      html = html.replace('<div class="pg plant">', `<div class="pg plant ${tab === "plant" ? "" : "hide"}">`);
      html += `<div class="hdr"><h1>${esc(this._config.title || this._topo.title || "ETA")}<span class="beta">BETA</span></h1>
        ${ctl ? `<div class="tabs"><button data-tab="plant" class="${tab === "plant" ? "act" : ""}">${this._t("tab_plant")}</button><button data-tab="ctl" class="${tab === "ctl" ? "act" : ""}">${this._t("tab_ctl")}</button></div>` : ""}
        <span class="m" id="outside"></span></div>`;
      cv.innerHTML = html;
      cv.querySelectorAll(".tabs button").forEach((btn) => btn.addEventListener("click", () => {
        this._tab = btn.dataset.tab;
        cv.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("act", x === btn));
        cv.querySelector(".pg.plant").classList.toggle("hide", this._tab !== "plant");
        cv.querySelector(".pg.ctl").classList.toggle("hide", this._tab !== "ctl");
      }));
      // on/off switches directly; switching off asks first, so nothing goes off by accident
      cv.querySelectorAll(".tg").forEach((el) => el.addEventListener("click", () => {
        const sw = el.dataset.sw;
        const want = !this._shownOn(sw);
        if (!want && !window.confirm(`${el.dataset.n} ${this._t("ask_off")}`)) return;
        // the state only updates with the next poll: show the new position until then
        this._swPending = this._swPending || {};
        this._swPending[sw] = { on: want, until: Date.now() + 180000 };
        this._call(el, sw, want ? "turn_on" : "turn_off");
        this._update();
      }));
      cv.querySelectorAll(".ts").forEach((el) => el.addEventListener("click", () => {
        const b = this._blocks.find((x) => x.id === el.dataset.ts);
        if (b) this._openTimes(b);
      }));
      cv.querySelectorAll(".md").forEach((el) => el.addEventListener("click", () => {
        if (el.classList.contains("act")) return;
        // the other mode keys only update with the next poll: show the chosen one alone until then
        this._pending = this._pending || {};
        this._pending[el.closest(".tile").dataset.tile] = { md: el.dataset.md, until: Date.now() + 180000 };
        // ETA keeps "Auto" on while a heat/setback key overrides it: writing "on" again
        // changes nothing, so the active override keys are switched off first
        const ends = [];
        if (el.dataset.mode === "auto") {
          el.closest(".modes").querySelectorAll(".md").forEach((o) => {
            if (o === el) return;
            [o.dataset.md, o.dataset.also].filter((e) => e && this._isOn(e)).forEach((e) => ends.push(e));
          });
        }
        this._call(el, el.dataset.md, "turn_on", ends);
        this._update();
      }));
      // every value and status chip opens its own entity, the rest of the block the status
      cv.querySelectorAll("[data-e],[data-chip],[data-ash],[data-hop]").forEach((el) => el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: el.dataset.e || el.dataset.chip || el.dataset.ash || el.dataset.hop }, bubbles: true, composed: true }));
      }));
      cv.querySelectorAll("[data-hint]").forEach((el) => el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this._hint(el.dataset.hint);
      }));
      const outEl = cv.querySelector("#outside");
      if (outEl) outEl.addEventListener("click", () => {
        const out = this._topo.plant && this._topo.plant.outside;
        if (out) this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: out }, bubbles: true, composed: true }));
      });
      cv.querySelectorAll(".blk").forEach((el) => {
        el.addEventListener("click", () => {
          const b = this._blocks.find((x) => x.id === el.dataset.b);
          const entityId = b.roles.status || Object.values(b.roles)[0] || b.entities[0];
          if (!entityId) return;
          this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
        });
      });
      this._built = true;
      this._builtLang = this._lang();
      if (!this._ro) {
        this._ro = new ResizeObserver(() => this._fit());
        this._ro.observe(this);
        window.addEventListener("resize", () => this._fit());
      }
      this._fit();
      this._update();
    }

    // highest hopper content of the last HOPPER_HOURS from the recorder, refreshed hourly
    _hopperFull(entityId) {
      this._hop = this._hop || {};
      const c = this._hop[entityId];
      if (!c || (!c.busy && Date.now() - c.t > 3600e3)) {
        this._hop[entityId] = { max: c ? c.max : null, t: Date.now(), busy: true };
        const start = new Date(Date.now() - HOPPER_HOURS * 3600e3).toISOString();
        this._hass.callWS({
          type: "history/history_during_period", start_time: start, entity_ids: [entityId],
          minimal_response: true, no_attributes: true, significant_changes_only: false,
        }).then((res) => {
          const vals = (res[entityId] || []).map((x) => Number(x.s ?? x.state)).filter((x) => !Number.isNaN(x));
          const max = vals.length ? Math.max(...vals) : null;
          this._hop[entityId] = { max: max && max > 1 ? max : null, t: Date.now(), busy: false };
          this._update();
        }).catch(() => { this._hop[entityId] = { max: null, t: Date.now(), busy: false }; });
      }
      return this._hop[entityId].max;
    }

    // above the boiler: ash box (first boiler) and pellet hopper, one bar each
    _boilerRows(b, first) {
      if (b.type !== "boiler") return "";
      const plant = this._topo.plant || {};
      const rows = [];
      if (first && plant.ash_fill) rows.push(`<div class="ashrow" data-ash="${plant.ash_fill}">${ashSvg(22)}<div class="ashbar"><i></i></div><span class="pc"></span></div>`);
      if (b.roles.hopper) rows.push(`<div class="ashrow hop" data-hop="${b.roles.hopper}">${hopSvg(22)}<div class="ashbar"><i></i></div><span class="pc"></span></div>`);
      return rows.length ? `<div class="rows">${rows.join("")}</div>` : "";
    }

    // second tab: boiler / heating circuit control via the integration's switches
    _controlHtml() {
      // SH-TWIN: both parts get their own tile (own status and on/off)
      const all = this._blocks.flatMap((b) => (b.partner ? [b, b.partner] : [b]));
      const tiles = all.filter((b) => b.roles.switch || b.roles.heat || b.roles.auto || b.roles.lower);
      const plant = this._topo.plant || {};
      const side = this._topo.blocks.filter((b) => SIDE_ICONS[b.type]);
      const epHtml = side.map((b) => {
        const st = b.roles.status || this._guessStatus(b);
        const ret = b.roles.return ? `<div class="vrow"><div class="pill" data-e="${b.roles.return}"></div></div>` : "";
        return `<div class="tile" data-tile="${b.id}"><div class="th">
          <img src="${iconSrc(SIDE_ICONS[b.type].off)}" data-ep="${st || ""}" data-side="${b.type}">
          <div class="tx"><div class="tn">${this._name(b)}</div>${st ? `<div class="chip" data-chip="${st}"></div>` : ""}</div>
        </div>${ret}</div>`;
      }).join("");
      if (!tiles.length && epHtml) return `<div class="tiles">${epHtml}</div>`;
      if (!tiles.length) {
        const any = this._blocks.some((b) => ["boiler", "heating_circuit"].includes(b.type));
        return any ? `<div class="tiles"><div class="empty">${this._t("no_ctl")}</div></div>` : null;
      }
      const geo = Object.fromEntries(this._geo.map((g) => [g.b.id, g]));
      const svg = (body) => `<svg viewBox="0 0 40 40" width="38" height="38" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round">${body}</svg>`;
      const rays = [0, 45, 90, 135, 180, 225, 270, 315].map((d) => {
        const r = (d * Math.PI) / 180;
        return `<line x1="${20 + 12 * Math.cos(r)}" y1="${20 + 12 * Math.sin(r)}" x2="${20 + 17 * Math.cos(r)}" y2="${20 + 17 * Math.sin(r)}"/>`;
      }).join("");
      const modes = [
        ["heat", svg(`<circle cx="20" cy="20" r="7" fill="currentColor"/>${rays}`)],
        // crescent lit on the left side, as on the ETA terminal
        ["lower", svg(`<path d="M24 4.5A16 16 0 1 0 35.5 24 13 13 0 0 1 24 4.5Z" fill="currentColor" stroke="none"/>`)],
        ["auto", svg(`<circle cx="20" cy="20" r="15"/><path d="M20 10v10l7 4"/>`)],
      ];
      return `<div class="tiles">${tiles.map((b) => {
        const name = this._name(b);
        const vals = (TOP_VALUES[b.type] || []).filter((r) => b.roles[r]).slice(0, 2)
          .map((r) => `<div class="pill" data-e="${b.roles[r]}"></div>`).join("");
        // temporary keys when available: "Heizen" = ETA "Kommen" (until the next setback time),
        // "Absenken" = ETA "Gehen" (until the next heating time)
        const temp = { heat: "come", lower: "go" };
        const target = (r) => (temp[r] && b.roles[temp[r]]) || b.roles[r];
        const m = modes.filter(([r]) => target(r)).map(([r, ic]) => {
          const also = temp[r] && b.roles[temp[r]] && b.roles[r] ? ` data-also="${b.roles[r]}"` : "";
          return `<button class="md" data-mode="${r}" data-md="${target(r)}"${also}><i>${ic}</i>${this._t(r)}</button>`;
        }).join("");
        return `<div class="tile" data-tile="${b.id}">
          <div class="th">${geo[b.id] ? `<img src="${iconSrc(geo[b.id].file)}">`
            : DEFAULT_BY_OBJECT[b.object] ? `<img src="${iconSrc(DEFAULT_BY_OBJECT[b.object][0])}">` : ""}
            <div class="tx"><div class="tn">${name}</div>${b.roles.status ? `<div class="chip" data-chip="${b.roles.status}"></div>` : ""}</div>
            ${b.roles.switch ? `<div class="tg" data-sw="${b.roles.switch}" data-n="${name}">0<b></b>I</div>` : ""}
          </div>
          ${vals ? `<div class="vrow">${vals}</div>` : ""}
          ${b.type === "boiler" && plant.ash_fill && b === this._blocks.find((x) => x.type === "boiler")
            ? `<div class="ash" data-ash="${plant.ash_fill}">${ashSvg(38)}
                <div class="col"><div class="tx"><b></b><span></span></div><div class="bar"><i></i></div><div class="fc"></div></div></div>` : ""}
          ${b.roles.hopper ? `<div class="ash hop" data-hop="${b.roles.hopper}">${hopSvg(38)}
                <div class="col"><div class="tx"><b></b><span></span></div><div class="bar"><i></i></div></div></div>` : ""}
          ${m ? `<div class="modes">${m}</div>` : ""}
          ${b.roles.slot_0_0 || b.roles.slot_6_2 ? `<div class="ts" data-ts="${b.id}"><div class="bar"></div>
            <div class="ax">${[0, 6, 12, 18, 24].map((h) => `<span style="left:${h / 24 * 100}%">${h}</span>`).join("")}</div></div>` : ""}
        </div>`;
      }).join("")}${epHtml}</div>`;
    }

    // no detection rule for the separator status yet: take the first text value of the
    // block (e.g. "Bereit"); a value picked under "Werte zuordnen" replaces it
    _guessStatus(b) {
      return b.entities.find((e) => {
        const st = this._hass.states[e];
        return st && e.startsWith("sensor.") && !(st.attributes || {}).unit_of_measurement
          && /^[^\d]+$/.test(String(st.state)) && !["unknown", "unavailable"].includes(st.state);
      }) || null;
    }

    // "06:00 - 21:00" or "06:00 - 21:00: 21 °C" -> [start, end] in minutes, null if empty
    _slot(entityId) {
      const st = entityId && this._hass.states[entityId];
      const m = st && String(st.state).match(/(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})/);
      if (!m) return null;
      const a = +m[1] * 60 + +m[2];
      const z = +m[3] * 60 + +m[4];
      return z > a ? [a, z] : null;
    }

    // "06:00 - 21:00" or "06:00 - 21:00 21" -> {a, z, t}; empty slot = 00:00 - 00:00
    _slotVal(entityId) {
      const st = entityId && this._hass.states[entityId];
      const m = st && String(st.state).match(/(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\D*([\d.,]+)?/);
      const pad = (h, mi) => `${String(h).padStart(2, "0")}:${mi}`;
      if (!m) return { a: "00:00", z: "00:00", t: null };
      return { a: pad(m[1], m[2]), z: pad(m[3], m[4]), t: m[5] ? Number(m[5].replace(",", ".")) : null };
    }

    // heating times editor: one weekday, three slots, optionally copied to other days
    _openTimes(b) {
      const root = this.shadowRoot;
      const t = (k) => this._t(k);
      let day = (new Date().getDay() + 6) % 7;
      const ent = (d, n) => b.roles[`slot_${d}_${n}`];
      const feat = (e) => Number(((this._hass.states[e] || {}).attributes || {}).supported_features || 0);
      const dlg = document.createElement("div");
      dlg.className = "dlg";
      root.appendChild(dlg);
      const close = () => dlg.remove();
      const render = () => {
        const writable = [0, 1, 2].some((n) => feat(ent(day, n)));
        const rows = [0, 1, 2].map((n) => {
          const e = ent(day, n);
          if (!e) return "";
          const v = this._slotVal(e);
          const dis = feat(e) ? "" : "disabled";
          const temp = feat(e) & 2 ? `<input type="number" step="0.5" data-t="${n}" value="${v.t ?? ""}" ${dis}> °C` : "";
          return `<div class="sl">${n + 1}. ${t("from")} <input type="time" step="900" data-a="${n}" value="${v.a}" ${dis}>
            ${t("to")} <input type="time" step="900" data-z="${n}" value="${v.z === "24:00" ? "23:59" : v.z}" ${dis}> ${temp}</div>`;
        }).join("");
        dlg.innerHTML = `<div class="in"><h2>${t("times")} – ${this._name(b)}</h2>
          <div class="dy">${t("days").map((d, i) => `<button data-d="${i}" class="${i === day ? "act" : ""}">${d}</button>`).join("")}</div>
          ${rows}
          ${writable ? `<div class="ap">${t("apply")} <select id="ap">
            <option value="day">${t("only_day")}</option><option value="wd">${t("workdays")}</option>
            <option value="we">${t("weekend")}</option><option value="all">${t("all_days")}</option></select></div>`
            : `<div class="hint">${t("ro")}</div>`}
          <div class="msg"></div>
          <div class="bt"><button class="no">${t("cancel")}</button>${writable ? `<button class="ok">${t("save")}</button>` : ""}</div></div>`;
        dlg.querySelectorAll(".dy button").forEach((x) => x.addEventListener("click", () => { day = +x.dataset.d; render(); }));
        dlg.querySelector(".no").addEventListener("click", close);
        const ok = dlg.querySelector(".ok");
        if (ok) ok.addEventListener("click", () => save(ok));
      };
      const save = async (ok) => {
        const msg = dlg.querySelector(".msg");
        const val = (sel) => { const x = dlg.querySelector(sel); return x ? x.value : ""; };
        const slots = [0, 1, 2].map((n) => ({
          a: val(`[data-a="${n}"]`) || "00:00", z: val(`[data-z="${n}"]`) || "00:00", t: val(`[data-t="${n}"]`),
        }));
        if (slots.some((x) => x.a > x.z)) { msg.textContent = t("bad_slot"); return; }
        const ap = val("#ap");
        const days = { day: [day], wd: [0, 1, 2, 3, 4], we: [5, 6], all: [0, 1, 2, 3, 4, 5, 6] }[ap] || [day];
        ok.disabled = true;
        msg.style.color = "#aaa";
        msg.textContent = t("saving");
        try {
          for (const d of days) {
            for (const n of [0, 1, 2]) {
              const e = ent(d, n);
              const f = feat(e);
              if (!e || !f) continue;
              const want = slots[n];
              const cur = this._slotVal(e);
              const temp = f & 2 ? Number(String(want.t || cur.t || 0).replace(",", ".")) : null;
              const z = want.z === "23:59" ? "24:00" : want.z;
              if (cur.a === want.a && cur.z === z && (temp === null || temp === cur.t)) continue; // unchanged
              const data = { entity_id: e, begin: `${want.a}:00`, end: `${want.z}:00` };
              if (temp !== null) data.temperature = temp;
              await this._hass.callService("eta_webservices", temp !== null ? "write_timeslot_plus_temperature" : "write_timeslot", data);
            }
          }
          close();
        } catch (err) {
          ok.disabled = false;
          msg.style.color = "";
          msg.textContent = String(err && err.message ? err.message : err);
        }
      };
      dlg.addEventListener("click", (ev) => { if (ev.target === dlg) close(); });
      render();
    }

    async _call(el, entityId, service, offFirst = []) {
      el.classList.add("busy");
      const dom = (e) => (e.startsWith("switch.") ? "switch" : "homeassistant");
      try {
        for (const e of offFirst) await this._hass.callService(dom(e), "turn_off", { entity_id: e });
        await this._hass.callService(dom(entityId), service, { entity_id: entityId });
      } finally {
        setTimeout(() => el.classList.remove("busy"), 1500);
      }
    }

    // up to two meaningful measurements of a block without known roles
    _autoValues(b) {
      const units = ["°C", "%", "bar", "kg"];
      return (b.entities || []).filter((e) => {
        const st = this._hass.states[e];
        if (!st || Number.isNaN(Number(st.state))) return false;
        return units.includes(st.attributes.unit_of_measurement) && !e.endsWith("_writable");
      }).sort((x, y) => units.indexOf(this._hass.states[x].attributes.unit_of_measurement)
        - units.indexOf(this._hass.states[y].attributes.unit_of_measurement)).slice(0, 2);
    }

    _roleLabel(type, role) {
      const row = (EDIT_ROLES[type] || []).find((r) => r[0] === role);
      return row ? row[this._lang() === "de" ? 1 : 2] : role;
    }

    // short note for a value that is not selected in the integration
    _hint(title) {
      const dlg = document.createElement("div");
      dlg.className = "dlg";
      dlg.innerHTML = `<div class="in"><h2>${esc(title)}</h2><div>${esc(this._t("hint_selected"))}</div>
        <div class="bt"><button class="no">OK</button></div></div>`;
      this.shadowRoot.appendChild(dlg);
      dlg.addEventListener("click", (ev) => { if (ev.target === dlg || ev.target.classList.contains("no")) dlg.remove(); });
    }

    _name(b) {
      if (b.label) return esc(b.label);
      let n = (b.name || "").split(">").pop().trim();
      const title = (this._topo.title || "").trim();
      if (title && n.toLowerCase().startsWith(title.toLowerCase() + " ")) n = n.slice(title.length + 1);
      return n.replace(/\[/g, "(").replace(/\]/g, ")") || this._t(b.object === "10281" ? "external_heat" : b.type);
    }

    // pellet hoses need room between store and boiler: move the store image left, then
    // shrink it; its values and name stay centred in the column
    _roomForHoses() {
      const si = this._geo.findIndex((g) => g.b.type === "silo");
      const st = this._geo[si];
      const bo = this._geo[si + 1];
      if (!st || !bo || bo.b.type !== "boiler" || NO_HOSE.test(bo.file)) return;
      let lack = HOSE_GAP - (bo.left - st.right);
      if (lack <= 0) return;
      const move = Math.min(lack, Math.max(0, st.left - 8));
      lack -= move;
      let k = 1;
      if (lack > 0) k = Math.max(0.6, 1 - lack / (st.right - st.left));
      const left = st.left - move;
      const w = st.w * k;
      const h = st.h * k;
      const x0 = left - st.bx[0] * w;
      const sink = (1 - st.bx[3]) * h;
      const y0 = FLOOR - h + sink;
      Object.assign(st, {
        w, h, x0, y0, sink, dx: x0 + w / 2 - st.cx, left, right: x0 + st.bx[2] * w, bodyRight: x0 + st.body[1] * w,
        top: y0 + st.bx[1] * h, bottom: y0 + st.bx[3] * h,
      });
    }

    _pipes() {
      const g = this._geo;
      const find = (t) => g.find((x) => x.b.type === t);
      const silo = find("silo") || find("chip_store");
      const boilers = g.filter((x) => x.b.type === "boiler");
      const buffers = g.filter((x) => x.b.type === "buffer");
      const boiler = boilers[0];
      const icons = this._config.icons || {};
      const heats = g.filter((x) => isHeat(x.b, icons));
      const consumers = g.filter((x) => CONSUMERS.includes(x.b.type) && !heats.includes(x));
      const T = 9;
      const BEND = 5; // radius of the dash curve at pipe bends
      const ys = FLOOR - 300; // supply line height, above the consumers and their values
      const yr = ys + 34; // return runs close below the supply
      const segs = [];
      // one straight pipe piece; dir +1 = flow towards (x2,y2)
      const seg = (x1, y1, x2, y2, cls) => {
        const hz = y1 === y2;
        segs.push({ cls, hz, x1: Math.min(x1, x2), x2: Math.max(x1, x2), y1: Math.min(y1, y2), y2: Math.max(y1, y2) });
        const l = Math.min(x1, x2) - T / 2;
        const t = Math.min(y1, y2) - T / 2;
        const w = hz ? Math.abs(x2 - x1) + T : T;
        const h = hz ? T : Math.abs(y2 - y1) + T;
        return `<div class="p ${cls} ${hz ? "h" : "v"}" style="left:${l}px;top:${t}px;width:${w}px;height:${h}px"></div>`;
      };
      // dash: the path of the moving dashes, may reach a little into the pipe it branches off
      // phase: {start: g} or {end: g}, the position g on the trunk where the dashes start or end,
      // so the dash pattern runs on across joints instead of starting anew in every piece
      const line = (pts, cls, dash = pts, phase = null) => {
        let out = "";
        for (let i = 1; i < pts.length; i++) out += seg(pts[i - 1][0], pts[i - 1][1], pts[i][0], pts[i][1], cls);
        pts = dash;
        // dashes run along the whole line in flow direction, with a small curve at each bend
        let d = `M${pts[0][0]} ${pts[0][1]}`;
        let len = 0;
        for (let i = 1; i < pts.length; i++) {
          const [x, y] = pts[i];
          const [px, py] = pts[i - 1];
          len += Math.hypot(x - px, y - py);
          const next = pts[i + 1];
          if (!next) { d += `L${x} ${y}`; break; }
          const r = Math.min(BEND, Math.hypot(x - px, y - py) / 2, Math.hypot(next[0] - x, next[1] - y) / 2);
          const ux = Math.sign(x - px), uy = Math.sign(y - py);
          const vx = Math.sign(next[0] - x), vy = Math.sign(next[1] - y);
          if (ux !== vx || uy !== vy) len -= 0.38 * r; // the curve is a little shorter than the corner
          d += `L${x - ux * r} ${y - uy * r}Q${x} ${y} ${x + vx * r} ${y + vy * r}`;
        }
        const o = !phase ? 0 : "start" in phase ? phase.start : phase.end - len;
        const st = o ? ` style="--o:${(((o % 24) + 24) % 24).toFixed(1)}px"` : "";
        return `${out}<svg class="fl ${cls}"><path d="${d}"${st}/></svg>`;
      };
      const group = (key, inner) => `<div class="g" data-flow="${key}">${inner}</div>`;
      let s = "";
      this._hoseLeft = null;
      if (silo && boiler) {
        if (silo.b.type === "silo" && NO_HOSE.test(boiler.file)) {
          // log or wood chip boiler: no pellet suction
        } else if (silo.b.type === "silo") {
          // pellet suction system: suction hose (pellets to the boiler) and return air
          // hose (back to the store), side by side without crossing: the return hose
          // leaves the store higher, runs on the outer side and ends at the farther stub
          const D = 14; // distance between the two hoses
          const y0 = silo.top + (silo.bottom - silo.top) * 0.4;
          const st = STUBS[boiler.file];
          const f = FEED[boiler.file];
          let ends; // [x, y of the run towards the boiler, y where the hose ends]
          if (st) {
            // from above into the two stubs on the boiler roof
            const top = boiler.y0 + st[2] * boiler.h;
            ends = {
              suction: [boiler.x0 + st[0] * boiler.w, top - 10, top + 2],
              air: [boiler.x0 + st[1] * boiler.w, top - 10 - D, top + 2],
            };
          } else {
            // sideways into the boiler, at its hopper
            const xe = (f ? boiler.x0 + f[0] * boiler.w : boiler.left) + 3;
            const yb = f ? boiler.y0 + f[1] * boiler.h : boiler.top + (boiler.bottom - boiler.top) * 0.16;
            ends = { suction: [xe, yb + D / 2, null], air: [xe, yb - D / 2, null] };
          }
          // risers in the middle of the gap between store and boiler; the outer (air)
          // riser is left of the suction riser when going up, right when going down
          const xc = (silo.right + Math.min(boiler.left, ends.suction[0])) / 2;
          const up = ends.suction[1] < y0;
          const xs = xc + (up ? D / 2 : -D / 2);
          const xa = xc + (up ? -D / 2 : D / 2);
          const path = (x, ya, e) => {
            const pts = [[silo.right - 6, ya], [x, ya], [x, e[1]], [e[0], e[1]]];
            if (e[2] !== null) pts.push([e[0], e[2]]);
            return pts;
          };
          this._hoseLeft = Math.min(xs, xa) - T / 2;
          const suction = path(xs, y0 + D / 2, ends.suction);
          const air = path(xa, y0 - D / 2, ends.air).reverse(); // flows back to the store
          s += group(silo.b.id, line(suction, "pe") + line(air, "air"));
        } else {
          // wood chip discharge auger at floor level
          const y = Math.min(silo.bottom, boiler.bottom) - 34;
          s += group(silo.b.id, `<div class="band" style="left:${silo.right - 10}px;top:${y}px;width:${boiler.left - silo.right + 20}px"><i></i></div>`);
        }
      }
      // producers at device height: boiler 1 -> boiler 2 -> buffer 1 -> buffer 2 carry flow when a
      // boiler runs; other heat sources charge the buffer in parallel on their own lines
      const chain = [...boilers, ...heats, ...buffers].sort((p, q) => p.cx - q.cx);
      const ysb = FLOOR - 190;
      const allBoilers = [...boilers, ...heats].map((x) => x.b.id).join(",");
      // lines start and end a little inside the devices (hidden behind the images), so they
      // never stop short of a soft image edge
      const pair = (a, b, y, key) => group(key,
        line([[a.bodyRight - 10, y], [b.left + 10, y]], "vl") +
        line([[b.left + 10, y + 34], [a.bodyRight - 10, y + 34]], "rl"));
      // boilers and buffers in a row; boilers pass behind a heat source straight to the buffer
      const main = chain.filter((x) => !heats.includes(x));
      const boilerKey = boilers.map((x) => x.b.id).join(",");
      // both lines of a pair must lie inside both devices (a small boiler in a narrow column sits low)
      const fits = (a, b) => [Math.max(a.top, b.top) + 14, Math.min(a.bottom, b.bottom) - 48];
      const cross = {}; // height of the boiler lines passing behind each heat source
      const mains = []; // drawn after the heat sources, which may share them
      for (let i = 1; i < main.length; i++) {
        const a = main[i - 1];
        const b = main[i];
        const key = a.b.type === "boiler" && b.b.type === "boiler" ? a.b.id : boilerKey;
        const [lo, hi] = fits(a, b);
        let y = Math.min(Math.max(ysb, lo), hi);
        // the supply line stays visible just above a heat source that reaches up to it
        // (the return passes behind)
        const between = heats.filter((h) => h.cx > a.cx && h.cx < b.cx);
        const low = Math.min(...between.map((h) => h.top - 10));
        if (between.length && low >= lo && low < y) y = low;
        const m = { a, b, y, key };
        between.forEach((h) => { cross[h.b.id] = m; });
        mains.push(m);
      }
      // each heat source has its own lines, lower down, into the next part on its right
      // (heat pump: out of the outdoor unit); with nothing on its right it joins from the left.
      // Several heat sources feeding the same part get their lines one above the other.
      const used = [];
      [...heats].sort((p, q) => q.cx - p.cx).forEach((h) => {
        const next = main.find((x) => x.cx > h.cx);
        const prev = [...main].reverse().find((x) => x.cx < h.cx);
        const other = next || prev;
        if (!other) return;
        const [lo0, hi] = fits(h, other);
        const behind = cross[h.b.id];
        const lo = Math.max(lo0, behind ? behind.y + 58 : -Infinity);
        const want = Math.min(Math.max(h.y0 + (HEAT_PIPE_Y[h.file] || 0.6) * h.h, lo), hi);
        const free = (y) => y >= lo - 0.5 && y <= hi + 0.5 && used.every((u) => u.to !== other || Math.abs(u.y - y) >= 68);
        const y = [0, 68, -68, 136, -136].map((d) => want + d).find(free);
        if (y === undefined) {
          // no room for another pair (narrow columns): join the heat source next to it
          const near = heats.filter((x) => x !== h && (next ? x.cx > h.cx : x.cx < h.cx))
            .sort((p, q) => Math.abs(p.cx - h.cx) - Math.abs(q.cx - h.cx))[0];
          if (near) {
            const yy = used.find((u) => u.h === near)?.y ?? want;
            s += next ? pair(h, near, yy, h.b.id) : pair(near, h, yy, allBoilers);
            used.push({ h, to: near, y: yy });
          } else if (behind) {
            // tiny devices: the boiler line behind it carries its heat too
            behind.key = [behind.key, h.b.id].filter(Boolean).join(",");
          } else {
            s += next ? pair(h, next, want, h.b.id) : pair(prev, h, want, allBoilers);
          }
          return;
        }
        used.push({ h, to: other, y });
        s += next ? pair(h, next, y, h.b.id) : pair(prev, h, y, allBoilers);
      });
      mains.forEach((m) => { if (m.key) s += pair(m.a, m.b, m.y, m.key); });
      const src = buffers[buffers.length - 1] || chain[chain.length - 1];
      if (src) {
        // supply line above the producer (boiler without buffer): both lines drop
        // straight into its top (the image hides the rest), so none starts in the air
        const air = src.top > ys - 4;
        // risers come out of the tank body (not out of a tap beside it)
        const xR = src.bodyRight - 44;
        const xB = src.bodyRight - 20;
        const yIn = src.top + (src.bottom - src.top) * 0.2;
        const head = air ? [[xR, yIn], [xR, ys]] : [[src.bodyRight, ys]];
        const tail = air ? [[xB, yr], [xB, yIn]] : [[src.bodyRight, yr]];
        // each consumer: own riser and connection; the shared trunk lines along ys / yr
        // are drawn once, piece by piece, so no two pipes lie on top of each other
        const legs = consumers.map((c) => {
          const a = c.anchors;
          const inX = a ? c.x0 + a.in[0] * c.w : c.left;
          const inY = a ? c.y0 + a.in[1] * c.h : c.top + (c.bottom - c.top) * 0.3;
          const out = a && a.out;
          const outX = out ? c.x0 + out[0] * c.w : c.left;
          const outY = out ? c.y0 + out[1] * c.h : c.top + (c.bottom - c.top) * 0.8;
          // the riser of the upper connection sits closer to the icon
          const returnAbove = out && out[2] === "h" && outY < inY;
          let xv = returnAbove ? inX - 64 : inX - 30; // supply riser
          let xr = returnAbove ? inX - 30 : xv - 34; // return riser
          // a consumer right next to the producer: keep both risers clear of its edge
          const minX = src.right + 24;
          if (Math.min(xv, xr) < minX) {
            const gap = Math.max(12, Math.min(34, inX - 8 - minX));
            if (returnAbove) { xv = minX; xr = Math.max(minX + gap, Math.min(xr, inX - 8)); } else { xr = minX; xv = minX + gap; }
          }
          let rl;
          if (out && out[2] === "u") {
            xr = outX;
            rl = [[outX, outY], [outX, yr]];
          } else if (out && out[2] === "v") {
            rl = [[outX, outY], [outX, outY + 10], [xr, outY + 10], [xr, yr]];
          } else {
            rl = [[outX, outY], [xr, outY], [xr, yr]];
          }
          return { id: c.b.id, xv, xr, vl: [[xv, ys], [xv, inY], [inX, inY]], rl };
        });
        const ids = (xs) => xs.map((l) => l.id).join(",");
        const all = ids(legs);
        if (legs.length) {
          if (head.length > 1) s += group(all, line(head, "vl", head, { end: head[head.length - 1][0] }));
          if (tail.length > 1) s += group(all, line(tail, "rl", tail, { start: -tail[0][0] }));
        }
        // supply trunk: from the producer to each riser; a piece carries flow when a consumer behind it runs
        const bySup = [...legs].sort((p, q) => p.xv - q.xv);
        const lastV = Math.max(...legs.map((l) => l.xv));
        const lastR = Math.max(...legs.map((l) => l.xr));
        let x = head[head.length - 1][0];
        bySup.forEach((l, i) => {
          // the last piece ends in a bend: its dashes stop short and the riser's curve takes over
          const endV = l.xv === lastV ? l.xv - BEND : l.xv;
          if (l.xv > x) s += group(ids(bySup.slice(i)), line([[x, ys], [l.xv, ys]], "vl", [[x, ys], [endV, ys]], { start: x }));
          x = Math.max(x, l.xv);
        });
        const byRet = [...legs].sort((p, q) => p.xr - q.xr);
        x = tail[0][0];
        byRet.forEach((l, i) => {
          const startR = l.xr === lastR ? l.xr - BEND : l.xr;
          if (l.xr > x) s += group(ids(byRet.slice(i)), line([[l.xr, yr], [x, yr]], "rl", [[startR, yr], [x, yr]], { start: -startR }));
          x = Math.max(x, l.xr);
        });
        // branch dashes curve out of / into the trunk instead of starting on it
        const x0 = head[head.length - 1][0];
        const x1 = tail[0][0];
        legs.forEach((l) => {
          const vl = [[l.xv + (l.xv >= x0 ? -BEND : BEND), ys], ...l.vl];
          const rl = [...l.rl, [l.xr + (l.xr >= x1 ? -BEND : BEND), yr]];
          s += group(l.id, line(l.vl, "vl", vl, { start: vl[0][0] }) + line(l.rl, "rl", rl, { end: -rl[rl.length - 1][0] }));
        });
      }
      // supply crossing a return pipe: the supply runs on top, the return gets a gap (bridge)
      const vl = segs.filter((x) => x.cls === "vl");
      const rl = segs.filter((x) => x.cls === "rl");
      const seen = new Set();
      for (const a of vl) {
        for (const b of rl) {
          if (a.hz === b.hz) continue;
          const v = a.hz ? b : a;
          const h = a.hz ? a : b;
          const x = v.x1;
          const y = h.y1;
          if (x <= h.x1 + T || x >= h.x2 - T || y <= v.y1 + T || y >= v.y2 - T) continue;
          const key = `${Math.round(x)},${Math.round(y)}`;
          if (seen.has(key)) continue;
          seen.add(key);
          const along = T + 10;
          const across = T + 2;
          const [w, hh] = h === b ? [along, across] : [across, along];
          s += `<div class="gap" style="left:${x - w / 2}px;top:${y - hh / 2}px;width:${w}px;height:${hh}px"></div>`;
        }
      }
      return s;
    }

    _fit() {
      const box = this.shadowRoot && this.shadowRoot.querySelector(".box");
      const cv = this.shadowRoot && this.shadowRoot.querySelector(".cv");
      if (!box || !cv) return;
      const sw = box.clientWidth / W;
      if (!sw) { requestAnimationFrame(() => this._fit()); return; }
      // never taller than the visible area below the card top (panel / full screen view)
      const top = Math.max(0, box.getBoundingClientRect().top + window.scrollY);
      const avail = window.innerHeight - Math.min(top, window.innerHeight / 2) - 12;
      const s = avail > 200 ? Math.min(sw, avail / H) : sw;
      cv.style.transform = `scale(${s})`;
      cv.style.left = `${(box.clientWidth - W * s) / 2}px`;
      box.style.height = `${H * s}px`;
    }

    _fmt(entityId) {
      const st = this._hass.states[entityId];
      if (!st) return null;
      const unit = st.attributes.unit_of_measurement || "";
      let v = st.state;
      const num = Number(v);
      if (v !== "" && !Number.isNaN(num)) {
        const digits = unit === "bar" ? 2 : unit === "l/min" ? 1 : 0;
        v = num.toLocaleString(this._hass.locale ? this._hass.locale.language : undefined, {
          maximumFractionDigits: digits, minimumFractionDigits: digits,
        });
      }
      // forecasts in days: "≈ 41 Tage"
      if (unit === "d") return `≈ ${v}<u> ${this._t("d_unit")}</u>`;
      return `${v}<u>${unit}</u>`;
    }

    // "leeren in ca. 3 Wochen" from a number of days
    _when(days) {
      if (days <= 0) return this._t("empty_now");
      if (days < 14) return this._t("in_days")(Math.round(days));
      if (days < 60) return this._t("in_weeks")(Math.round(days / 7));
      return this._t("in_months")(Math.round(days / 30));
    }

    // switch position on the card: a pending click wins until the poll confirms it
    _shownOn(sw) {
      const on = this._isOn(sw);
      const p = this._swPending && this._swPending[sw];
      if (p && (Date.now() > p.until || p.on === on)) delete this._swPending[sw];
      return this._swPending && this._swPending[sw] ? this._swPending[sw].on : on;
    }

    _modeOn(el) {
      return this._isOn(el.dataset.md) || (el.dataset.also ? this._isOn(el.dataset.also) : false);
    }

    _isOn(entityId) {
      const st = this._hass.states[entityId];
      if (!st) return false;
      const num = Number(st.state);
      if (!Number.isNaN(num)) return num > 0;
      return ON.includes(String(st.state).toLowerCase());
    }

    _isIdle(entityId) {
      const st = this._hass.states[entityId];
      if (!st) return true;
      const v = String(st.state).toLowerCase();
      // ETA texts like "Aus Heizgrenze [Absenken]" or "Bereit" count as idle
      return IDLE.some((w) => v === w || v.startsWith(`${w} `));
    }

    // the store's values must not cover the pellet hoses: move them left as far as
    // needed, but not past the left edge of the card
    _valsOffHoses() {
      const vals = this._hoseLeft && this.shadowRoot.querySelector(".blk.t-silo .vals");
      const cv = this.shadowRoot.querySelector(".cv");
      if (!vals || !cv) return;
      vals.style.transform = "";
      const c = cv.getBoundingClientRect();
      const k = c.width / W;
      if (!k) return;
      const r = vals.getBoundingClientRect();
      const left = (r.left - c.left) / k;
      const over = (r.right - c.left) / k - (this._hoseLeft - 10);
      const shift = Math.max(0, Math.min(over, left - 8));
      if (shift > 0) vals.style.transform = `translateX(${-shift}px)`;
    }

    _update() {
      const root = this.shadowRoot;
      if (!root || !this._topo) return;
      let resized = false;
      root.querySelectorAll("[data-e]").forEach((el) => {
        // no value (e.g. flow temperature while the circuit is off, forecast without history): hide the box
        const st = this._hass.states[el.dataset.e];
        const na = !st || ["unknown", "unavailable", "", "---", "xxx"].includes(String(st.state));
        if (el._na !== na) { el.classList.toggle("na", na); el._na = na; resized = true; }
        const v = this._fmt(el.dataset.e);
        const html = v === null ? "–" : v;
        if (el._v !== html) { el.innerHTML = html; el._v = html; resized = true; }
      });
      if (resized) this._valsOffHoses();
      // ash box: bar colour from 80 % (soon) and 100 % (ETA asks to empty it)
      root.querySelectorAll("[data-ash]").forEach((el) => {
        const st = this._hass.states[el.dataset.ash];
        const v = st ? Number(st.state) : NaN;
        const ok = !Number.isNaN(v);
        el.classList.toggle("warn", ok && v >= 80 && v < 100);
        el.classList.toggle("full", ok && v >= 100);
        el.querySelector("i").style.width = `${ok ? Math.min(Math.max(v, 0), 100) : 0}%`;
        const pc = el.querySelector(".pc");
        if (pc) pc.textContent = ok ? `${Math.round(v)} %` : "–";
        const tx = el.querySelector(".tx");
        if (tx) {
          const days = this._hass.states[(this._topo.plant || {}).ash_days];
          const d = days ? Number(days.state) : NaN;
          tx.querySelector("b").textContent = `${this._t("ash")} ${ok ? Math.round(v) : "–"} %`;
          tx.querySelector("span").textContent = ok && v >= 100 ? this._t("empty_now") : Number.isNaN(d) ? "" : this._when(d);
          const m = this._hass.states[(this._topo.plant || {}).method];
          const fc = el.querySelector(".fc");
          const label = m && !Number.isNaN(d) ? this._t(`fc_${m.state}`) : "";
          if (fc) fc.textContent = label.startsWith("fc_") ? "" : label;
        }
      });
      // pellet hopper: kg against the highest value of the last 48 h (see HOPPER_HOURS)
      root.querySelectorAll("[data-hop]").forEach((el) => {
        const st = this._hass.states[el.dataset.hop];
        const v = st ? Number(st.state) : NaN;
        const ok = !Number.isNaN(v);
        const learned = this._hopperFull(el.dataset.hop);
        const full = Math.max(learned || HOPPER_KG, ok ? v : 0);
        const pct = ok && full > 0 ? Math.min(Math.max(v / full, 0), 1) * 100 : 0;
        el.querySelector("i").style.width = `${pct}%`;
        const kg = ok ? `${Math.round(v)} kg` : "–";
        const pc = el.querySelector(".pc");
        if (pc) pc.textContent = ok ? `${Math.round(pct)} %` : "–";
        const tx = el.querySelector(".tx");
        if (tx) {
          tx.querySelector("b").textContent = `${this._t("hopper")} ${kg}`;
          tx.querySelector("span").textContent = ok ? `${Math.round(pct)} %` : "";
        }
      });
      root.querySelectorAll("[data-chip]").forEach((el) => {
        const id = el.dataset.chip;
        const st = this._hass.states[id];
        // ETA status texts like "Ein [Heizen]" -> "Ein Heizen"; SH-TWIN: "Pellets: …" / "Holz: …"
        const raw = st ? String(st.state).replace(/[[\]]/g, " ").replace(/\s+/g, " ").trim() : "–";
        const txt = el.dataset.pre ? `${el.dataset.pre}: ${raw}` : raw;
        if (el.textContent !== txt) el.textContent = txt;
        el.classList.toggle("idle", this._isIdle(id));
      });
      root.querySelectorAll(".tg").forEach((el) => {
        const on = this._shownOn(el.dataset.sw);
        if (el._on !== on) { el.classList.toggle("on", on); el._on = on; }
      });
      root.querySelectorAll(".modes").forEach((row) => {
        const key = row.closest(".tile").dataset.tile;
        const btns = [...row.querySelectorAll(".md")];
        // one mode lights up: heat / setback override the time program, which ETA keeps "on" meanwhile
        const cur = (btns.find((el) => this._modeOn(el)) || {}).dataset;
        const p = this._pending && this._pending[key];
        // after a click the chosen key shows until the next poll confirms it (or times out)
        if (p && (Date.now() > p.until || (cur && cur.md === p.md))) delete this._pending[key];
        const show = (this._pending && this._pending[key] && this._pending[key].md) || (cur && cur.md);
        btns.forEach((el) => {
          const on = el.dataset.md === show;
          if (el._on !== on) { el.classList.toggle("act", on); el._on = on; }
        });
      });
      const now = new Date();
      const day = (now.getDay() + 6) % 7;
      root.querySelectorAll(".ts").forEach((el) => {
        const b = this._blocks.find((x) => x.id === el.dataset.ts);
        if (!b) return;
        const ranges = [0, 1, 2].map((n) => this._slot(b.roles[`slot_${day}_${n}`])).filter(Boolean);
        const pos = ((now.getHours() * 60 + now.getMinutes()) / 1440) * 100;
        const html = ranges.map(([a, z]) => `<div class="w" style="left:${a / 14.4}%;width:${(z - a) / 14.4}%"></div>`).join("")
          + `<div class="now" style="left:${pos.toFixed(1)}%"></div>`;
        const bar = el.querySelector(".bar");
        if (bar._v !== html) { bar.innerHTML = html; bar._v = html; }
      });
      const out = this._topo.plant && this._topo.plant.outside;
      const o = root.getElementById("outside");
      const outOk = out && this._hass.states[out] && !Number.isNaN(Number(this._hass.states[out].state));
      if (o) o.innerHTML = outOk ? `${this._t("outside")} <b>${this._fmt(out).replace(/<\/?u>/g, " ")}</b>` : "";
      // flows
      const active = (b) => {
        if (!b) return false;
        if (b.partner && active(b.partner)) return true;
        // a value picked by hand in the settings decides first: pump, else status
        const picked = b.picked || [];
        if (picked.includes("pump")) return this._isOn(b.roles.pump);
        if (picked.includes("status")) return !this._isIdle(b.roles.status);
        if (b.roles.pump) return this._isOn(b.roles.pump);
        if (b.roles.auger && this._isOn(b.roles.auger)) return true;
        if (b.roles.discharge && this._isOn(b.roles.discharge)) return true;
        if (b.roles.auger) return b.roles.status ? !this._isIdle(b.roles.status) : false;
        return b.roles.status ? !this._isIdle(b.roles.status) : false;
      };
      root.querySelectorAll("[data-flow]").forEach((el) => {
        const on = el.dataset.flow.split(",").some((key) => active(this._blocks.find((x) => x.id === key)));
        if (el._on !== on) { el.classList.toggle("on", on); el.classList.toggle("off", !on); el._on = on; }
      });
      root.querySelectorAll("img[data-ep]").forEach((img) => {
        const ic = SIDE_ICONS[img.dataset.side] || SIDE_ICONS.particle_separator;
        const file = img.dataset.ep && !this._isIdle(img.dataset.ep) ? ic.on : ic.off;
        if (!img.src.includes(file)) img.src = iconSrc(file);
      });
      // other heat sources: flame / coloured fan only while running, same test as their lines
      root.querySelectorAll("img[data-onoff]").forEach((img) => {
        const on = img.dataset.onoff;
        const b = this._blocks.find((x) => x.id === img.closest(".blk").dataset.b);
        const file = active(b) ? on : on.replace(/_ein\.webp$/, "_aus.webp");
        if (!img.src.includes(file)) img.src = iconSrc(file);
      });
      // radiator / underfloor heating: the "off" picture while the circuit does not run
      root.querySelectorAll("img[data-type=heating_circuit]").forEach((img) => {
        const b = this._blocks.find((x) => x.id === img.closest(".blk").dataset.b);
        const shown = img.dataset.file || ICONS.heating_circuit[0];
        if (!HK_OFF.test(shown)) return;
        // same rule as the lines: a hand-picked value first, else the pump
        const off = b && (b.roles.pump || (b.picked || []).length) && !active(b);
        const file = off ? shown.replace(/_ein\.webp$/, "_aus.webp") : shown;
        const src = iconSrc(file);
        if (!img.src.includes(file)) img.src = src;
      });
    }
  }

  // Target of the "report plant" button.
  const REPORT_REPO = "meinETA/homeassistant-eta";

  // texts of the card settings
  const EDIT_TEXTS = {
    de: {
      settings: "Einstellungen", reset_all: "Alles zurücksetzen", cancel: "Abbrechen", save: "Speichern",
      order: "Reihenfolge", order_text: "Reihenfolge der Anlagenteile von links nach rechts, z. B. wie am ETA-Terminal.", up: "nach links", down: "nach rechts", order_reset: "Automatisch",
      auto: "Automatisch", plant: "Anlage", language: "Sprache", lang_auto: "Automatisch (HA)", title: "Name der Anlage",
      store: "Lager", no_icons: "Keine Anlagenteile mit Icon-Auswahl erkannt.", loading: "Anlage wird geladen …",
      report: "Anlage melden",
      report_text: "Wird deine Anlage nicht richtig dargestellt? „GitHub-Issue öffnen“ lädt die Anlagendatei herunter und öffnet ein Formular auf GitHub. Zieh die Datei dort in das Feld „Plant file“. Die Datei enthält alle Werte der Anlage mit ETA-Namen, Einheiten und aktuellen Messwerten, aber keine IP-Adresse, keine Seriennummer, keine selbst vergebenen Namen und keinen Verlauf. Die Datei ist verschlüsselt, lesen können sie nur die Entwickler der Integration. Unten siehst du ihren Inhalt. Gesendet wird erst, wenn du das Issue auf GitHub selbst abschickst. Das Issue ist öffentlich sichtbar. Achte auf dem Screenshot auf persönliche Namen.",
      download: "Anlagendatei herunterladen", open_issue: "GitHub-Issue öffnen", file: "Inhalt der Datei (wird verschlüsselt)",
      seal_failed: "Die Anlagendatei konnte nicht verschlüsselt werden:",
    },
    en: {
      settings: "Settings", reset_all: "Reset everything", cancel: "Cancel", save: "Save",
      order: "Order", order_text: "Order of the plant parts from left to right, e.g. as on the ETA terminal.", up: "move left", down: "move right", order_reset: "Automatic",
      auto: "Automatic", plant: "Plant", language: "Language", lang_auto: "Automatic (HA)", title: "Plant name",
      store: "Store", no_icons: "No plant parts with an icon choice detected.", loading: "Loading plant …",
      report: "Report plant",
      report_text: "Is your plant not shown correctly? \u201cOpen GitHub issue\u201d downloads the plant file and opens a form on GitHub. Drag the file into the \u201cPlant file\u201d field there. The file contains every value of the plant with ETA names, units and current readings, but no IP address, no serial number, no names you gave and no history. The file is encrypted, only the developers of the integration can read it. Its content is shown below. Nothing is sent until you submit the issue on GitHub yourself. The issue is public. Check the screenshot for personal names.",
      download: "Download plant file", open_issue: "Open GitHub issue", file: "Content of the file (gets encrypted)",
      seal_failed: "The plant file could not be encrypted:",
    },
  };
  const REPORT_FILE = "eta-plant-report.json";
  // English names for the icon choices (ETA model names stay)
  const ICON_EN = {
    "Pelletslager": "Pellet store", "Saugsystem 3-fach": "Suction system 3-way", "Saugsystem 4-fach": "Suction system 4-way",
    "Saugsystem 8-fach": "Suction system 8-way", "Hackgut Rührwerk": "Wood chip agitator", "Hackgut Schnecke": "Wood chip auger",
    "Rührer": "Agitator", "Pendelschnecke": "Swinging auger", "Pendelschnecke 2-fach": "Swinging auger 2-way",
    "Schubboden": "Sliding floor", "Schubboden 2-fach": "Sliding floor 2-way", "Schubboden 3-fach": "Sliding floor 3-way",
    "PU / PC grau": "PU / PC grey", "ePE (gelb)": "ePE (yellow)", "ePE (Einblick)": "ePE (inside view)", "ePE BW (weiß)": "ePE BW (white)",
    "SH alt": "SH old", "SH-TWIN alt": "SH-TWIN old", "HACK VR (gelb)": "HACK VR (yellow)", "HACK VR (grau)": "HACK VR (grey)",
    "Puffer": "Buffer", "Puffer mit Wendel": "Buffer with coil", "Kombispeicher": "Combi tank", "Heizkörper": "Radiator",
    "Fußbodenheizung": "Underfloor heating", "Frischwassermodul": "Fresh water module", "FWM Brauchwasser": "FWM domestic water",
    "Modul": "Module", "Wärmepumpe": "Heat pump", "Öl-/Gasbrenner": "Oil / gas burner", "Biomasse": "Biomass",
  };

  class EtaPlantCardEditor extends HTMLElement {
    setConfig(config) {
      this._config = { ...config };
      this._render();
    }

    set hass(hass) {
      this._hass = hass;
      if (!this._topo && !this._loading) {
        this._loading = true;
        hass.callWS({ type: "eta_webservices/topology" }).then((all) => {
          this._all = all;
          const want = this._config && this._config.entry;
          this._topo = (want && all.find((e) => e.entry_id === want || e.title === want)) || all[0] || null;
          this._render();
        }).catch(() => { this._topo = null; this._all = []; this._render(); });
      }
    }

    _render() {
      if (!this._config) return;
      if (!this.shadowRoot) this.attachShadow({ mode: "open" });
      const T = EDIT_TEXTS[this._de() ? "de" : "en"];
      const icons = this._config.icons || {};
      const list = this._topo ? [...this._topo.blocks] : [];
      // plant parts added by hand get an icon choice too
      if (this._topo) (this._config.extra || []).forEach((x) => list.push({ id: x.id, type: x.type, name: null }));
      if (!list.some((b) => b.type === "silo")) {
        const bo = list.find((b) => b.type === "boiler" && b.roles.auger);
        if (bo) list.splice(list.indexOf(bo), 0, { id: `${bo.id}/store`, type: "chip_store", name: T.store });
      }
      const rows = list.filter((b) => ICON_CHOICES[b.type]).map((b) => {
        const name = esc((this._config.names || {})[b.id] || this._label(b));
        const opts = ICON_CHOICES[b.type].map(([label, file]) =>
          `<option value="${file}" ${webp(icons[b.id]) === file ? "selected" : ""}>${this._de() ? label : ICON_EN[label] || label}</option>`).join("");
        return `<label>${name}<select data-b="${b.id}"><option value="">${T.auto}</option>${opts}</select></label>`;
      }).join("");
      this.shadowRoot.innerHTML = `<style>
        label{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:8px 0;font-size:14px}
        select,input{min-width:200px;padding:6px;font-size:14px}
        .order{margin-top:20px;padding-top:12px;border-top:1px solid var(--divider-color,#444);font-size:13px}
        .order .ord{display:flex;align-items:center;gap:6px;margin:4px 0;font-size:14px}
        .order .ord span{flex:1}.order .ord.hid{opacity:.5}
        .order button{padding:3px 9px;cursor:pointer}
        .report{margin-top:20px;padding-top:12px;border-top:1px solid var(--divider-color,#444);font-size:13px}
        .report textarea{width:100%;box-sizing:border-box;font-family:monospace;font-size:11px;margin:8px 0}
        .report button{padding:6px 12px;cursor:pointer}
        .vals{margin-top:20px;padding-top:12px;border-top:1px solid var(--divider-color,#444);font-size:13px}
        .vals details{border:1px solid var(--divider-color,#444);border-radius:8px;margin:6px 0;padding:0 10px}
        .vals summary{cursor:pointer;padding:9px 0;font-size:14px;font-weight:500}
        .vals summary .tag{font-weight:400;opacity:.65;margin-left:6px}
        .vals summary .mod{font-size:11px;background:#ffc400;color:#1a1a1a;border-radius:6px;padding:1px 6px;margin-left:6px}
        .vals .row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:6px 0;font-size:14px}
        .vals .row select,.vals .row input[type=text]{min-width:0;width:62%}
        .vals .hid{opacity:.5}
        .vals .ft{display:flex;justify-content:space-between;gap:8px;margin:8px 0 10px}
        .vals .ft button,.vals .add button{padding:5px 10px;cursor:pointer}
        .vals .add{display:flex;gap:8px;align-items:center;margin-top:10px}
        .vals .danger{background:#c62828;color:#fff;border:1px solid #c62828;border-radius:4px}
      </style>
      ${this._all && this._all.length > 1 && !this.fixedEntry ? `<label>${T.plant}<select id="entry">${this._all.map((e) =>
        `<option value="${e.title}" ${this._topo && this._topo.entry_id === e.entry_id ? "selected" : ""}>${e.title}</option>`).join("")}</select></label>` : ""}
      <label>${T.language}<select id="lang">${[["", T.lang_auto], ["de", "Deutsch"], ["en", "English"]].map(([v, l]) =>
        `<option value="${v}" ${(this._config.language || "") === v ? "selected" : ""}>${l}</option>`).join("")}</select></label>
      <label>${T.title}<input id="title" value="${esc(this._config.title || "")}" placeholder="${esc((this._topo && this._topo.title) || "ETA")}"></label>
      ${rows || `<p>${this._all ? T.no_icons : T.loading}</p>`}
      ${this._topo ? this._orderHtml(T) : ""}
      ${this._topo ? this._valuesHtml() : ""}
      <div class="report">
        <b>${T.report}</b>
        <p>${T.report_text}</p>
        <button id="dl">${T.download}</button> <button id="gh">${T.open_issue}</button>
        ${this._sealErr ? `<p style="color:#e53935">${T.seal_failed} ${esc(this._sealErr)}</p>` : ""}
        ${this._report ? `<p>${T.file} <code>${REPORT_FILE}</code>:</p><textarea readonly rows="10">${esc(this._report)}</textarea>` : ""}
      </div>`;
      this.shadowRoot.getElementById("lang").addEventListener("change", (ev) => {
        const cfg = { ...this._config, language: ev.target.value };
        if (!cfg.language) delete cfg.language;
        this._emit(cfg);
      });
      this.shadowRoot.getElementById("title").addEventListener("change", (ev) => {
        const cfg = { ...this._config, title: ev.target.value.trim() };
        if (!cfg.title) delete cfg.title;
        this._emit(cfg);
      });
      const entrySel = this.shadowRoot.getElementById("entry");
      if (entrySel) entrySel.addEventListener("change", (ev) => {
        this._topo = this._all.find((e) => e.title === ev.target.value) || null;
        this._cands = null;
        const cfg = { ...this._config, entry: ev.target.value };
        delete cfg.icons; // icon choices belong to the previous plant
        this._emit(cfg);
        this._render();
      });
      this.shadowRoot.querySelectorAll("[data-mv]").forEach((btn) => btn.addEventListener("click", () => {
        const ids = this._orderIds();
        const i = +btn.dataset.mv;
        const j = i + +btn.dataset.d;
        if (j < 0 || j >= ids.length) return;
        [ids[i], ids[j]] = [ids[j], ids[i]];
        this._emit({ ...this._config, order: ids });
        this._render();
      }));
      const ordreset = this.shadowRoot.getElementById("ordreset");
      if (ordreset) ordreset.addEventListener("click", () => {
        const cfg = { ...this._config };
        delete cfg.order;
        this._emit(cfg);
        this._render();
      });
      this.shadowRoot.querySelectorAll("select[data-b]").forEach((sel) => sel.addEventListener("change", (ev) => {
        const next = { ...(this._config.icons || {}) };
        if (ev.target.value) next[ev.target.dataset.b] = ev.target.value;
        else delete next[ev.target.dataset.b];
        const cfg = { ...this._config, icons: next };
        if (!Object.keys(next).length) delete cfg.icons;
        this._emit(cfg);
      }));
      if (this._topo) this._wireValues();
      const $ = (id) => this.shadowRoot.getElementById(id);
      $("dl").addEventListener("click", async () => {
        if (await this._makeReport()) this._download();
        this._render();
      });
      $("gh").addEventListener("click", async () => {
        // open the window synchronously, otherwise the popup blocker kicks in
        const win = window.open("about:blank", "_blank");
        if (!(await this._makeReport())) { if (win) win.close(); this._render(); return; }
        // the encrypted plant file is downloaded and dragged into the issue form by the user
        this._download();
        const url = `https://github.com/${REPORT_REPO}/issues/new?template=plant-card.yml&title=${encodeURIComponent("Plant card: ")}`;
        if (win) win.location.href = url; else window.open(url, "_blank");
        this._render();
      });
    }

    // ---- "Werte zuordnen": pick the entity of a value by hand ----
    _de() {
      const h = this._hass || {};
      const l = this._config.language || (h.locale && h.locale.language) || h.language || "en";
      return l.startsWith("de");
    }

    _blockList() {
      const b = [{ id: "plant", type: "plant", name: this._de() ? "Ganze Anlage" : "Whole plant", roles: this._topo.plant || {}, entities: [] }];
      this._topo.blocks.filter((x) => EDIT_ROLES[x.type] || x.type === "unknown").forEach((x) => b.push(x));
      (this._config.extra || []).forEach((x) => b.push({ id: x.id, type: x.type, name: null, roles: {}, entities: [], manual: true }));
      return b;
    }

    _label(b) {
      const lab = LABELS[this._de() ? "de" : "en"];
      if (b.type === "plant") return b.name;
      let n = (b.name || "").split(">").pop().trim().replace(/\[/g, "(").replace(/\]/g, ")");
      const title = ((this._topo && this._topo.title) || "").trim();
      if (title && n.toLowerCase().startsWith(`${title.toLowerCase()} `)) n = n.slice(title.length + 1);
      return n || lab[b.type] || b.type;
    }

    // all ETA entities of this plant: those of the detected blocks plus every entity on the same devices
    _candidates() {
      if (this._cands) return this._cands;
      const ents = this._hass.entities || {};
      const set = new Set();
      this._topo.blocks.forEach((b) => b.entities.forEach((e) => set.add(e)));
      Object.values(this._topo.plant || {}).forEach((e) => set.add(e));
      const devices = new Set([...set].map((e) => ents[e] && ents[e].device_id).filter(Boolean));
      Object.values(ents).forEach((x) => {
        if (x.platform === "eta_webservices" && devices.has(x.device_id) && !x.entity_id.endsWith("_writable")) set.add(x.entity_id);
      });
      this._cands = [...set].filter((e) => this._hass.states[e]);
      return this._cands;
    }

    _fits(e, kind) {
      const st = this._hass.states[e];
      const unit = st.attributes.unit_of_measurement || "";
      const num = st.state !== "" && !Number.isNaN(Number(st.state));
      const dom = e.split(".")[0];
      if (kind === "temp") return unit === "°C" || unit === "K";
      if (kind === "bar") return unit === "bar";
      if (kind === "flow") return ["l/min", "l/h", "m³/h"].includes(unit);
      if (kind === "level") return ["kg", "%", "t"].includes(unit);
      if (kind === "switch") return dom === "switch";
      if (kind === "text") return dom === "sensor" && !num && !unit;
      if (kind === "onoff") return dom === "switch" || dom === "binary_sensor" || (dom === "sensor" && !unit);
      return true;
    }

    _optText(e) {
      const st = this._hass.states[e];
      const name = String(st.attributes.friendly_name || e).split(">").slice(-2).map((x) => x.trim()).join(" › ");
      const unit = st.attributes.unit_of_measurement || "";
      const v = String(st.state).length > 24 ? `${String(st.state).slice(0, 24)}…` : st.state;
      return `${name} – ${v}${unit ? ` ${unit}` : ""}`;
    }

    // current order of the plant parts (detected and added, hidden ones included)
    _orderIds() {
      const list = this._blockList().filter((b) => b.type !== "plant");
      const order = this._config.order || [];
      const pos = (b, i) => { const k = order.indexOf(b.id); return k < 0 ? order.length + i : k; };
      const sorted = list.map((b, i) => [pos(b, i), b]).sort((x, y) => x[0] - y[0]).map(([, b]) => b);
      return placeHeat(sorted, order, this._config.icons).map((b) => b.id);
    }

    _orderHtml(T) {
      const byId = Object.fromEntries(this._blockList().map((b) => [b.id, b]));
      const hidden = new Set(this._config.hidden || []);
      const ids = this._orderIds();
      if (ids.length < 2) return "";
      const rows = ids.map((id, i) => `<div class="ord${hidden.has(id) ? " hid" : ""}"><span>${esc(this._label(byId[id]))}</span>
        <button data-mv="${i}" data-d="-1" title="${T.up}" ${i === 0 ? "disabled" : ""}>◀</button>
        <button data-mv="${i}" data-d="1" title="${T.down}" ${i === ids.length - 1 ? "disabled" : ""}>▶</button></div>`).join("");
      return `<div class="order"><b>${T.order}</b><p>${T.order_text}</p>${rows}
        ${this._config.order ? `<button id="ordreset">${T.order_reset}</button>` : ""}</div>`;
    }

    _valuesHtml() {
      const de = this._de();
      const ov = this._config.roles || {};
      const hidden = new Set(this._config.hidden || []);
      const open = this._open || (this._open = new Set());
      const items = this._blockList().map((b) => {
        const changed = Object.keys(ov[b.id] || {}).length || (this._config.names || {})[b.id] || hidden.has(b.id);
        const tag = b.type === "plant" ? "" : `<span class="tag">${LABELS[de ? "de" : "en"][b.type] || ""}</span>`;
        return `<details data-bid="${b.id}" ${open.has(b.id) ? "open" : ""}>
          <summary class="${hidden.has(b.id) ? "hid" : ""}">${esc(this._label(b))}${tag}${changed ? `<span class="mod">${de ? "angepasst" : "changed"}</span>` : ""}</summary>
          <div class="body">${open.has(b.id) ? this._blockBody(b) : ""}</div></details>`;
      }).join("");
      const types = ADD_TYPES.map((t) => `<option value="${t}">${LABELS[de ? "de" : "en"][t]}</option>`).join("");
      return `<div class="vals"><b>${de ? "Werte manuell zuordnen" : "Assign values manually"}</b>
        <p>${de
          ? "Fehlt ein Wert, steht er an der falschen Stelle oder fehlt ein ganzes Anlagenteil? Klappe das Anlagenteil auf und wähle den passenden Wert aus der Liste. „Automatisch“ verwendet die Erkennung der Karte."
          : "Is a value missing, in the wrong place, or is a whole plant part missing? Open the plant part and pick the right value from the list. \u201cAutomatic\u201d uses the card's detection."}</p>
        <label class="row">${de ? "Werte per Entity-ID eingeben (zum Einfügen)" : "Enter values as entity ID (for pasting)"}
          <input type="checkbox" id="txtmode" ${this._txt ? "checked" : ""}></label>
        ${this._txt ? `<datalist id="ents">${this._candidates().map((e) => `<option value="${e}">${esc(this._optText(e))}</option>`).join("")}</datalist>` : ""}
        ${items}
        <div class="add">${de ? "Anlagenteil hinzufügen:" : "Add plant part:"} <select id="addtype">${types}</select>
          <button id="addbtn">${de ? "Hinzufügen" : "Add"}</button></div>
        ${this.fixedEntry ? "" : `<div class="ft"><span></span><button id="resetall" class="danger">${de ? "Alles zurücksetzen" : "Reset everything"}</button></div>`}</div>`;
    }

    _blockBody(b) {
      const de = this._de();
      const o = (this._config.roles || {})[b.id] || {};
      const cands = this._candidates();
      const own = new Set(b.entities || []);
      const rows = (EDIT_ROLES[b.type] || EDIT_ROLES.unknown).map(([role, lde, len, kind]) => {
        const cur = o[role] || "";
        const det = b.roles[role];
        const auto = det && this._hass.states[det] ? this._optText(det)
          : (b.unselected || {})[role] ? (de ? "in der Integration nicht ausgewählt" : "not selected in the integration")
          : (de ? "nichts erkannt" : "nothing detected");
        const fit = cands.filter((e) => this._fits(e, kind));
        fit.sort((x, y) => (own.has(y) - own.has(x)) || this._optText(x).localeCompare(this._optText(y)));
        const rest = cands.filter((e) => !fit.includes(e)).sort((x, y) => this._optText(x).localeCompare(this._optText(y)));
        const opt = (e) => `<option value="${e}" ${cur === e ? "selected" : ""}>${esc(this._optText(e))}</option>`;
        if (this._txt) {
          const bad = cur && cur !== "-" && !this._hass.states[cur];
          return `<label class="row">${de ? lde : len}<input type="text" list="ents" data-role="${role}" value="${esc(cur)}"
            placeholder="${de ? "leer = automatisch" : "empty = automatic"} (${esc(det || "–")})"
            ${bad ? `style="border-color:#e53935" title="${de ? "Entität nicht gefunden" : "Entity not found"}"` : ""}></label>`;
        }
        return `<label class="row">${de ? lde : len}<select data-role="${role}">
          <option value="">${de ? "Automatisch" : "Automatic"} (${esc(auto)})</option>
          <option value="-" ${cur === "-" ? "selected" : ""}>${de ? "– nicht anzeigen –" : "– do not show –"}</option>
          ${fit.length ? `<optgroup label="${de ? "Passende Werte" : "Matching values"}">${fit.map(opt).join("")}</optgroup>` : ""}
          ${rest.length ? `<optgroup label="${de ? "Alle anderen Werte" : "All other values"}">${rest.map(opt).join("")}</optgroup>` : ""}
        </select></label>`;
      }).join("");
      if (b.type === "plant") return rows;
      const name = (this._config.names || {})[b.id] || "";
      const hidden = (this._config.hidden || []).includes(b.id);
      return `<label class="row">${de ? "Name" : "Name"}<input type="text" data-name value="${esc(name)}" placeholder="${esc(this._label(b))}"></label>
        ${rows}
        <label class="row">${de ? "Auf der Karte anzeigen" : "Show on the card"}<input type="checkbox" data-show ${hidden ? "" : "checked"}></label>
        <div class="ft"><button data-reset>${de ? "Alles auf automatisch" : "Reset to automatic"}</button>
          ${b.manual ? `<button data-remove>${de ? "Anlagenteil entfernen" : "Remove plant part"}</button>` : ""}</div>`;
    }

    _wireValues() {
      const root = this.shadowRoot;
      const set = (patch) => {
        const cfg = { ...this._config, ...patch };
        ["roles", "names", "hidden", "extra"].forEach((k) => {
          const v = cfg[k];
          if (!v || (Array.isArray(v) ? !v.length : !Object.keys(v).length)) delete cfg[k];
        });
        this._emit(cfg);
        this._render();
      };
      root.querySelectorAll(".vals details").forEach((d) => {
        const bid = d.dataset.bid;
        d.addEventListener("toggle", () => {
          if (d.open) this._open.add(bid); else this._open.delete(bid);
          const body = d.querySelector(".body");
          if (d.open && !body.childElementCount) { this._render(); }
        });
        d.querySelectorAll("[data-role]").forEach((sel) => sel.addEventListener("change", () => {
          const roles = { ...(this._config.roles || {}) };
          const o = { ...(roles[bid] || {}) };
          const v = sel.value.trim();
          if (v) o[sel.dataset.role] = v; else delete o[sel.dataset.role];
          if (Object.keys(o).length) roles[bid] = o; else delete roles[bid];
          set({ roles });
        }));
        const nm = d.querySelector("[data-name]");
        if (nm) nm.addEventListener("change", () => {
          const names = { ...(this._config.names || {}) };
          if (nm.value.trim()) names[bid] = nm.value.trim(); else delete names[bid];
          set({ names });
        });
        const show = d.querySelector("[data-show]");
        if (show) show.addEventListener("change", () => {
          const hidden = (this._config.hidden || []).filter((x) => x !== bid);
          if (!show.checked) hidden.push(bid);
          set({ hidden });
        });
        const reset = d.querySelector("[data-reset]");
        if (reset) reset.addEventListener("click", () => {
          const roles = { ...(this._config.roles || {}) };
          const names = { ...(this._config.names || {}) };
          delete roles[bid];
          delete names[bid];
          set({ roles, names, hidden: (this._config.hidden || []).filter((x) => x !== bid) });
        });
        const rm = d.querySelector("[data-remove]");
        if (rm) rm.addEventListener("click", () => {
          const roles = { ...(this._config.roles || {}) };
          const names = { ...(this._config.names || {}) };
          delete roles[bid];
          delete names[bid];
          this._open.delete(bid);
          set({ roles, names, extra: (this._config.extra || []).filter((x) => x.id !== bid),
            hidden: (this._config.hidden || []).filter((x) => x !== bid) });
        });
      });
      const txt = root.getElementById("txtmode");
      if (txt) txt.addEventListener("change", () => { this._txt = txt.checked; this._render(); });
      const all = root.getElementById("resetall");
      if (all) all.addEventListener("click", () => this.resetValues());
      const add = root.getElementById("addbtn");
      if (add) add.addEventListener("click", () => {
        const id = `manual_${Date.now().toString(36)}`;
        this._open.add(id);
        set({ extra: [...(this._config.extra || []), { id, type: root.getElementById("addtype").value }] });
      });
    }

    // back to the automatic detection: drops all manual values, names, hidden and added parts
    resetValues() {
      if (!window.confirm(this._de()
        ? "Alle manuellen Zuordnungen, Namen, Reihenfolge, ausgeblendeten und hinzugefügten Anlagenteile löschen und wieder die automatische Erkennung verwenden?"
        : "Delete all manual values, names, order, hidden and added plant parts and use the automatic detection again?")) return;
      const cfg = { ...this._config };
      ["roles", "names", "hidden", "extra", "order"].forEach((k) => delete cfg[k]);
      this._open = new Set();
      this._emit(cfg);
      this._render();
    }

    async _makeReport() {
      // hand-picked values tell us which addresses the detection is missing
      const manual = [];
      const types = Object.fromEntries(this._blockList().map((b) => [b.id, b.type]));
      Object.entries(this._config.roles || {}).forEach(([bid, o]) => Object.entries(o).forEach(([role, e]) => {
        if (e && e !== "-" && types[bid]) manual.push([types[bid], role, e]);
      }));
      const rep = await this._hass.callWS({ type: "eta_webservices/report", entry_id: this._topo && this._topo.entry_id, manual, full: true });
      // card settings without user-given names: which parts are hidden, added or have another icon
      const c = this._config;
      const settings = {
        hidden: c.hidden || [], extra: (c.extra || []).map((x) => x.type), icons: c.icons || {},
        renamed: Object.keys(c.names || {}).length, language: c.language || "",
      };
      this._report = JSON.stringify({ card: ICON_REV, lang: this._hass.language, settings, ...rep }, null, 1);
      // the issue is public: the plant file is encrypted for the maintainers by the
      // integration; the text field above still shows the plain content
      try {
        const seal = async (text) => (await this._hass.callWS({ type: "eta_webservices/seal", data: text })).sealed;
        this._sealed = JSON.stringify({ eta_plant_file: "sealed", v: 1, data: await seal(JSON.stringify(JSON.parse(this._report))) });
        this._sealErr = null;
        return true;
      } catch (err) {
        this._sealed = null;
        this._sealErr = (err && err.message) || String(err);
        return false;
      }
    }

    _download() {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([this._sealed], { type: "application/json" }));
      a.download = REPORT_FILE;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    }

    _emit(config) {
      this._config = config;
      this.dispatchEvent(new CustomEvent("config-changed", { detail: { config }, bubbles: true, composed: true }));
    }
  }

  // Sidebar entry (one per plant): the card full screen; admins change its settings via the gear.
  class EtaPlantPanel extends HTMLElement {
    set hass(hass) {
      this._hass = hass;
      if (this._card) this._card.hass = hass;
      if (this._editor) this._editor.hass = hass;
      if (this._menu) this._menu.hass = hass;
      this._init();
    }

    set narrow(narrow) {
      this._narrow = narrow;
      if (this._menu) this._menu.narrow = narrow;
    }

    set panel(panel) {
      this._panel = panel;
      this._init();
    }

    async _init() {
      if (this._started || !this._hass || !this._panel) return;
      this._started = true;
      this._entry = this._panel.config.entry_id;
      let stored = {};
      try {
        stored = await this._hass.callWS({ type: "eta_webservices/panel_config", entry_id: this._entry });
      } catch (err) { /* no settings yet */ }
      this._cfg = { ...stored, entry: this._entry };
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `<style>
        :host{display:block;min-height:100vh;background:var(--primary-background-color,#111)}
        .bar{display:flex;align-items:center;height:48px;padding:0 8px}
        .sp{flex:1}
        .gear{background:none;border:0;color:var(--primary-text-color,#ddd);cursor:pointer;padding:8px;line-height:0;border-radius:50%}
        .gear:hover{background:rgba(127,127,127,.2)}
        .body{padding:0 12px 12px}
        .dlg{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:10}
        .dlg>div{background:var(--card-background-color,#1c1c1c);color:var(--primary-text-color,#ddd);border-radius:16px;
          padding:20px 24px;width:min(560px,calc(100vw - 32px));max-height:calc(100vh - 48px);overflow:auto;box-sizing:border-box}
        .dlg h2{margin:0 0 8px;font-size:20px}
        .act{display:flex;justify-content:flex-end;gap:8px;margin-top:16px}
        .act button{padding:8px 16px;border-radius:8px;border:1px solid var(--divider-color,#444);background:none;color:inherit;cursor:pointer;font:inherit}
        .act .save{background:var(--primary-color,#03a9f4);border-color:transparent;color:#fff}
        .act .reset{background:#c62828;border-color:transparent;color:#fff}
      </style>
      <div class="bar"><ha-menu-button></ha-menu-button><span class="sp"></span>${this._hass.user && this._hass.user.is_admin
        ? `<button class="gear" title="${this._texts().settings}"><svg viewBox="0 0 24 24" width="24" height="24"><path fill="currentColor" d="M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"/></svg></button>` : ""}</div>
      <div class="body"></div>`;
      this._menu = this.shadowRoot.querySelector("ha-menu-button");
      this._menu.hass = this._hass;
      this._menu.narrow = this._narrow;
      this._card = document.createElement("eta-plant-card");
      this._card.setConfig(this._cfg);
      this._card.hass = this._hass;
      this.shadowRoot.querySelector(".body").appendChild(this._card);
      const gear = this.shadowRoot.querySelector(".gear");
      if (gear) gear.addEventListener("click", () => this._openEditor());
    }

    // settings texts in the card language (panel setting, else Home Assistant)
    _texts() {
      const h = this._hass || {};
      const l = (this._cfg && this._cfg.language) || (h.locale && h.locale.language) || h.language || "en";
      return EDIT_TEXTS[l.startsWith("de") ? "de" : "en"];
    }

    _openEditor() {
      const saved = this._cfg;
      const T = this._texts();
      let draft = { ...saved };
      const dlg = document.createElement("div");
      dlg.className = "dlg";
      dlg.innerHTML = `<div><h2>${T.settings}</h2><div class="ed"></div>
        <div class="act"><button class="reset">${T.reset_all}</button><span class="sp"></span><button class="cancel">${T.cancel}</button><button class="save">${T.save}</button></div></div>`;
      this._editor = document.createElement("eta-plant-card-editor");
      this._editor.fixedEntry = true;
      this._editor.setConfig(draft);
      this._editor.hass = this._hass;
      this._editor.addEventListener("config-changed", (ev) => {
        ev.stopPropagation();
        draft = { ...ev.detail.config, entry: this._entry };
        this._card.setConfig(draft); // live preview
      });
      dlg.querySelector(".ed").appendChild(this._editor);
      const close = () => { dlg.remove(); this._editor = null; };
      dlg.querySelector(".cancel").addEventListener("click", () => { this._card.setConfig(saved); close(); });
      dlg.querySelector(".reset").addEventListener("click", () => this._editor.resetValues());
      dlg.querySelector(".save").addEventListener("click", async () => {
        const { entry, ...config } = draft;
        await this._hass.callWS({ type: "eta_webservices/panel_config/save", entry_id: this._entry, config });
        this._cfg = draft;
        close();
      });
      this.shadowRoot.appendChild(dlg);
    }
  }

  if (!customElements.get("eta-plant-panel")) {
    customElements.define("eta-plant-panel", EtaPlantPanel);
  }

  if (!customElements.get("eta-plant-card-editor")) {
    customElements.define("eta-plant-card-editor", EtaPlantCardEditor);
  }

  if (!customElements.get("eta-plant-card")) {
    customElements.define("eta-plant-card", EtaPlantCard);
    window.customCards = window.customCards || [];
    window.customCards.push({
      type: "eta-plant-card",
      name: (document.documentElement.lang || navigator.language || "").startsWith("de") ? "ETA Anlage" : "ETA Plant",
      description: "Übersicht der ETA-Heizanlage mit Live-Werten und Bedienung.",
    });
  }
})();
