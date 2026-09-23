"""Treatment advice per class, English (en) and Swahili (sw)."""

ADVICE = {
    "cbb": {
        "name": {"en": "Cassava Bacterial Blight (CBB)", "sw": "Ugonjwa wa Madoa ya Bakteria (CBB)"},
        "en": ("Sanitation and tool hygiene: remove and burn infected leaves and stems. "
               "Disinfect knives and hoes (e.g. bleach solution) between plants. "
               "Do not take cuttings from infected fields; plant clean, certified cuttings. "
               "Avoid working in the field when plants are wet. Rotate with a non-cassava crop."),
        "sw": ("Usafi na usafi wa zana: ondoa na uchome majani na mashina yaliyoathirika. "
               "Safisha visu na majembe (k.m. kwa maji ya bleach) kati ya mmea mmoja na mwingine. "
               "Usichukue vipandikizi kutoka shamba lililoathirika; panda vipandikizi safi vilivyothibitishwa. "
               "Epuka kufanya kazi shambani mimea ikiwa na maji. Badilisha zao kwa zao lisilo muhogo."),
    },
    "cbsd": {
        "name": {"en": "Cassava Brown Streak Disease (CBSD)", "sw": "Ugonjwa wa Michirizi ya Kahawia (CBSD)"},
        "en": ("CBSD is a virus spread mainly through infected planting material (and whiteflies). "
               "ROGUE: uproot and destroy infected plants now — they will not recover and roots may rot. "
               "Use ONLY clean cuttings from certified or inspected disease-free sources; never take "
               "cuttings from this plant or field. Plant tolerant varieties where available. "
               "Harvest early if roots are affected. Leaf symptoms can be faint — report to your extension officer."),
        "sw": ("CBSD ni virusi vinavyoenea hasa kupitia vipandikizi vilivyoathirika (na inzi weupe). "
               "NG'OA: ng'oa na uharibu mimea iliyoathirika sasa — haitapona na mizizi inaweza kuoza. "
               "Tumia vipandikizi SAFI TU kutoka vyanzo vilivyothibitishwa bila ugonjwa; usichukue vipandikizi "
               "kutoka mmea au shamba hili. Panda aina zinazostahimili ugonjwa. Vuna mapema ikiwa mizizi "
               "imeathirika. Dalili za majani zinaweza kufifia — mjulishe afisa ugani."),
    },
    "cgm": {
        "name": {"en": "Cassava Green Mite (CGM)", "sw": "Utitiri Kijani wa Muhogo (CGM)"},
        "en": ("Mite management: damage is worst in the dry season. Plant early so crops are established "
               "before the dry season. Encourage natural enemies (predatory mites such as Typhlodromalus "
               "aripo) — avoid broad-spectrum insecticides that kill them. Remove heavily infested shoot "
               "tips. Use tolerant (hairy-leaf) varieties. Mulch and good soil fertility help plants recover."),
        "sw": ("Udhibiti wa utitiri: madhara ni makubwa wakati wa kiangazi. Panda mapema ili mimea ikue "
               "kabla ya kiangazi. Linda maadui wa asili (utitiri wawindaji kama Typhlodromalus aripo) — "
               "epuka viuatilifu vinavyoua wadudu wote. Ondoa ncha za matawi zilizoathirika sana. Tumia aina "
               "zinazostahimili (majani yenye manyoya). Matandazo na rutuba nzuri husaidia mimea kupona."),
    },
    "cmd": {
        "name": {"en": "Cassava Mosaic Disease (CMD)", "sw": "Ugonjwa wa Batobato (CMD)"},
        "en": ("CMD is a virus spread mainly through infected cuttings (and whiteflies). "
               "ROGUE: uproot and destroy infected plants early, especially young ones, to protect the rest. "
               "Use ONLY clean, disease-free cuttings from certified sources for the next planting; never "
               "replant cuttings from infected plants. Plant CMD-resistant varieties. Keep fields weed-free."),
        "sw": ("CMD ni virusi vinavyoenea hasa kupitia vipandikizi vilivyoathirika (na inzi weupe). "
               "NG'OA: ng'oa na uharibu mimea iliyoathirika mapema, hasa michanga, kulinda mingine. "
               "Tumia vipandikizi SAFI TU visivyo na ugonjwa kutoka vyanzo vilivyothibitishwa; usipande "
               "tena vipandikizi kutoka mimea iliyoathirika. Panda aina zinazostahimili CMD. Palilia shamba."),
    },
    "healthy": {
        "name": {"en": "Healthy", "sw": "Mzima"},
        "en": ("No disease detected. Keep monitoring every 2 weeks, keep the field weeded, and continue "
               "to use clean cuttings. Check leaves from the top, middle and bottom of several plants."),
        "sw": ("Hakuna ugonjwa uliogunduliwa. Endelea kukagua kila wiki 2, palilia shamba, na endelea "
               "kutumia vipandikizi safi. Kagua majani ya juu, kati na chini ya mimea kadhaa."),
    },
}

UNCERTAIN = {
    "name": {"en": "Uncertain", "sw": "Haijulikani"},
    "en": ("The diagnosis is uncertain — ask an extension officer. Take 3–6 clear photos of leaves from the "
           "top, middle and bottom of the same plant in good daylight and try again."),
    "sw": ("Utambuzi haujakamilika — muulize afisa ugani. Piga picha 3–6 wazi za majani ya juu, kati na "
           "chini ya mmea mmoja kwenye mwanga mzuri wa mchana na ujaribu tena."),
}


def get_advice(label: str, lang: str = "en") -> dict:
    lang = lang if lang in ("en", "sw") else "en"
    entry = ADVICE.get(label, UNCERTAIN)
    return {"name": entry["name"][lang], "text": entry[lang], "lang": lang}
