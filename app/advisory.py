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


# Short farmer-facing card content: one-liner + at most 4 bullets per language.
CARD = {
    "cbb": {
        "summary": {"en": "A bacterial disease that spreads on tools, rain splash and cuttings.",
                    "sw": "Ugonjwa wa bakteria unaoenea kupitia zana, matone ya mvua na vipandikizi."},
        "bullets": {"en": ["Remove and burn infected leaves and stems.",
                           "Clean knives and hoes with bleach between plants.",
                           "Plant only clean, certified cuttings.",
                           "Rotate with a non-cassava crop next season."],
                    "sw": ["Ondoa na uchome majani na mashina yaliyoathirika.",
                           "Safisha visu na majembe kwa bleach kati ya mimea.",
                           "Panda vipandikizi safi vilivyothibitishwa tu.",
                           "Panda zao lisilo muhogo msimu ujao."]},
    },
    "cbsd": {
        "summary": {"en": "A virus that rots the roots. It spreads mainly through infected cuttings.",
                    "sw": "Virusi vinavyooza mizizi. Huenea hasa kupitia vipandikizi vilivyoathirika."},
        "bullets": {"en": ["Uproot and destroy infected plants now.",
                           "Never take cuttings from this plant or field.",
                           "Replant only clean cuttings from a certified source.",
                           "Check roots and harvest early if they are affected."],
                    "sw": ["Ng'oa na uharibu mimea iliyoathirika sasa.",
                           "Usichukue vipandikizi kutoka mmea au shamba hili.",
                           "Panda tena vipandikizi safi kutoka chanzo kilichothibitishwa tu.",
                           "Kagua mizizi na uvune mapema ikiwa imeathirika."]},
    },
    "cgm": {
        "summary": {"en": "Tiny mites that feed on young leaves, worst in the dry season.",
                    "sw": "Utitiri wadogo wanaokula majani machanga, hasa wakati wa kiangazi."},
        "bullets": {"en": ["Plant early so crops are strong before the dry season.",
                           "Avoid broad insecticides — they kill the mites' natural enemies.",
                           "Remove heavily infested shoot tips.",
                           "Use tolerant, hairy-leaf varieties."],
                    "sw": ["Panda mapema ili mimea iwe imara kabla ya kiangazi.",
                           "Epuka viuatilifu vya jumla — vinaua maadui wa asili wa utitiri.",
                           "Ondoa ncha za matawi zilizoathirika sana.",
                           "Tumia aina zinazostahimili zenye majani ya manyoya."]},
    },
    "cmd": {
        "summary": {"en": "A virus that twists and yellows leaves. It spreads mainly through infected cuttings.",
                    "sw": "Virusi vinavyokunja na kufanya majani kuwa manjano. Huenea hasa kupitia vipandikizi."},
        "bullets": {"en": ["Uproot and destroy infected plants early.",
                           "Never replant cuttings from infected plants.",
                           "Use clean cuttings of a CMD-resistant variety.",
                           "Keep the field weeded."],
                    "sw": ["Ng'oa na uharibu mimea iliyoathirika mapema.",
                           "Usipande tena vipandikizi kutoka mimea iliyoathirika.",
                           "Tumia vipandikizi safi vya aina inayostahimili CMD.",
                           "Palilia shamba."]},
    },
    "healthy": {
        "summary": {"en": "No disease was found on these leaves.",
                    "sw": "Hakuna ugonjwa uliopatikana kwenye majani haya."},
        "bullets": {"en": ["Check your plants again in 2 weeks.",
                           "Keep the field weeded.",
                           "Keep using clean cuttings."],
                    "sw": ["Kagua mimea yako tena baada ya wiki 2.",
                           "Palilia shamba.",
                           "Endelea kutumia vipandikizi safi."]},
    },
    "uncertain": {
        "summary": {"en": "The photos were not clear enough for a confident answer.",
                    "sw": "Picha hazikuwa wazi vya kutosha kupata jibu la uhakika."},
        "bullets": {"en": ["Show this plant to an extension officer.",
                           "Retake 3–6 photos in good daylight, one leaf per photo."],
                    "sw": ["Mwonyeshe afisa ugani mmea huu.",
                           "Piga tena picha 3–6 kwenye mwanga mzuri, jani moja kwa kila picha."]},
    },
}


def get_advice(label: str, lang: str = "en") -> dict:
    lang = lang if lang in ("en", "sw") else "en"
    entry = ADVICE.get(label, UNCERTAIN)
    card = CARD.get(label, CARD["uncertain"])
    return {"name": entry["name"][lang], "text": entry[lang], "lang": lang,
            "summary": card["summary"][lang], "bullets": card["bullets"][lang]}


def get_advice_all(label: str) -> dict:
    """Advice in every language, so the UI can switch language without a new request."""
    return {lang: get_advice(label, lang) for lang in ("en", "sw")}
