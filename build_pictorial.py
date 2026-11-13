"""Builds pictorial.json + pictorial.js for the pictorial round from questions_en.json.

Usage:  python build_pictorial.py [path/to/questions_en.json] [path/to/pictures]
  - the optional pictures folder is scanned: each subfolder is matched to a place below
    (exact, then close spelling); unmatched folders are reported.

A question joins a place if any of its terms/subs appears in the question or answer
(only inside `only` sections when given), or if its section is in `sections`.
Place terms in the question text are replaced by `generic`; `subs` are custom rewrites run first.
Answers are never changed. `reveals` marks questions whose answer is the place itself (shown last)."""
import json, re, sys, os, difflib
SEC = {1:(1,15),2:(16,23),3:(24,25),4:(26,44),5:(45,59),6:(60,74),7:(75,89),8:(90,100),9:(101,108),
       10:(109,127),11:(128,169),12:(170,191),13:(192,200),14:(201,243),15:(244,256),16:(257,275)}
def sec(i): return next(s for s,(a,b) in SEC.items() if a<=i<=b)
ORG, PLACE, BLD, PARK, AWD, PROG, NET = ("this institution","this place","this building","this park",
                                         "this award","this programme","this network")
def P(name, terms, generic=PLACE, sections=(), only=(), abbr=None, aliases=(), subs=()):
    al = list(aliases)
    if abbr: al += [abbr, f"{name} ({abbr})"]
    return dict(name=name, terms=list(terms), generic=generic, sections=list(sections), only=list(only),
                aliases=al, subs=list(subs))
CENTRE = lambda city, extra=(), al=(): P(f"Ismaili Centre, {city}",
    [f"Ismaili Centre, {city}", f"Ismaili Centre {city}", *extra], BLD, only=[4],
    aliases=[f"Ismaili Centre {city}", f"Ismaili Center {city}", f"Ismaili Center, {city}", *al])
PLACES = [
 # --- AKDN and agencies ---
 P("Aga Khan Development Network",["Aga Khan Development Network","AKDN"],NET,[7],abbr="AKDN"),
 P("Aga Khan Foundation",["Aga Khan Foundation","AKF"],ORG,[8],abbr="AKF"),
 P("Aga Khan Agency for Habitat",["Aga Khan Agency for Habitat","AKAH"],ORG,[9],abbr="AKAH"),
 P("Aga Khan Health Services",["Aga Khan Health Services","Aga Khan Health Service","AKHSP","AKHS"],ORG,[10],abbr="AKHS",aliases=["Aga Khan Health Service"]),
 P("Aga Khan University",["Aga Khan University Examination Board","Aga Khan University Hospital, Nairobi",
   "Aga Khan University Hospital","Aga Khan University","AKU-EB","AKU-SONAM","AKUH Karachi","AKUH Nairobi","AKUH","AKU"],
   ORG,[11],abbr="AKU",aliases=["Aga Khan University Hospital"]),
 P("University of Central Asia",["University of Central Asia","UCA"],ORG,[13],abbr="UCA"),
 P("Aga Khan Trust for Culture",["Aga Khan Trust for Culture","AKTC"],ORG,[14],abbr="AKTC"),
 P("Aga Khan Agency for Microfinance",["Aga Khan Agency for Microfinance","AKAM","First MicroFinance Bank",
   "FMFB-PAKISTAN","FMFB-Tajikistan","FMFB-A"],ORG,[15],abbr="AKAM"),
 P("Aga Khan Fund for Economic Development",["Aga Khan Fund for Economic Development","AKFED"],ORG,[16],abbr="AKFED"),
 P("Aga Khan Education Service",["Aga Khan Education Services","Aga Khan Education Service","Aga Khan Schools","AKES","AKS"],
   ORG,[12],abbr="AKES",aliases=["Aga Khan Education Services","Aga Khan Schools"]),
 P("Aga Khan Academy",["Aga Khan Academies","Aga Khan Academy Hyderabad - India","Aga Khan Academy, Mombasa",
   "Aga Khan Academy Mombasa","Aga Khan Academy Hyderabad","Aga Khan Academy Dhaka","Aga Khan Academy Maputo",
   "Aga Khan Academy","AKA"],ORG,abbr="AKA",aliases=["Aga Khan Academies"]),
 P("IIS",["The Institute of Ismaili Studies","Institute of Ismaili Studies","IIS"],ORG,[6],
   aliases=["Institute of Ismaili Studies"]),
 P("UNESCO",["UNESCO"],"this organisation",subs=[
   ("Which UNESCO honour","Which honour from this organisation"),
   ("UNESCO Asia-Pacific Heritage Awards","Asia-Pacific Heritage Awards from this organisation"),
   ("a UNESCO Asia-Pacific Heritage Award","an Asia-Pacific Heritage Award from this organisation"),
   ("a UNESCO Award for Distinction","an Award for Distinction from this organisation")]),
 # --- places and programmes ---
 P("Diwan of Ismaili Imamat, Portugal",["Diwan of the Ismaili Imamat","Seat of the Ismaili Imamat","Seat of Ismaili Imamat","Lisbon"],
   BLD,only=[1],aliases=["Diwan of the Ismaili Imamat","Diwan of Ismaili Imamat","Diwan","Seat of the Ismaili Imamat"],
   subs=[("the Seat of the Ismaili Imamat in Lisbon","this building"),("a formal Seat","a formal home for this building")]),
 P("Serena Hotels",["Islamabad Serena Hotel","Dushanbe Serena Hotel","Serena Shigar Fort","Serena Khaplu Palace","Serena Hotels"],
   "this hotel",aliases=["Serena Hotel","Serena"]),
 P("Aga Khan Museum, Toronto",["Aga Khan Museum in Toronto","Aga Khan Museum, Toronto","Aga Khan Museum"],"this museum",
   aliases=["Aga Khan Museum","Aga Khan Museum Toronto"]),
 P("Al-Azhar Park, Cairo",["Al-Azhar Park in Cairo","Al-Azhar Park, Cairo","Al-Azhar Park"],PARK,
   aliases=["Al-Azhar Park","Al Azhar Park","Al Azhar Park Cairo"]),
 P("Aga Khan Park, Toronto",["Aga Khan Park in Toronto","Aga Khan Park, Toronto","Aga Khan Park"],PARK,
   aliases=["Aga Khan Park","Aga Khan Park Toronto"]),
 P("Aga Khan Center",["Aga Khan Centre","Aga Khan Center"],BLD,[6],aliases=["Aga Khan Centre","Aga Khan Centre London"]),
 P("Aga Khan Award for Architecture",["Aga Khan Award for Architecture"],AWD),
 P("Aga Khan Music Awards",["Aga Khan Music Awards","Aga Khan Music Award","AKMA"],AWD,aliases=["Aga Khan Music Award"]),
 # --- Ismaili Centres ---
 CENTRE("London",["London"]),
 CENTRE("Vancouver",["Burnaby","Vancouver"],["Ismaili Centre Burnaby","Ismaili Centre, Burnaby"]),
 CENTRE("Lisbon",["Lisbon"]),
 CENTRE("Dubai",["Dubai"]),
 CENTRE("Dushanbe",["Dushanbe"]),
 CENTRE("Toronto",["Toronto"]),
 CENTRE("Houston",["Ismaili Center","Houston"]),
 # --- others ---
 P("Aga Khan Academy, Mombasa",["Aga Khan Academy, Mombasa","Aga Khan Academy Mombasa","Mombasa"],ORG,
   aliases=["Aga Khan Academy Mombasa","Aga Khan Academy, Mombasa"],
   subs=[("the first Aga Khan Academy open in Mombasa","this institution open")]),
 P("Citadel of Aleppo",["Citadel of Aleppo","Aleppo"],PLACE,aliases=["Aleppo Citadel","Aleppo"]),
 P("FOCUS",["Focus Humanitarian Assistance","FOCUS"],"this organisation",aliases=["Focus Humanitarian Assistance"],
   subs=[("Focus Humanitarian Assistance (FOCUS)","this organisation")]),
 P("Global Encounters",["Global Encounters Festival","Global Encounters Camp","Global Encounters","Kenya GE Camp","GE Camps","GE Camp"],
   PROG,aliases=["Global Encounters Camp","GE"],
   subs=[("the long-run GE Camps participation record","this programme's long-run participation record"),
         ("the first Global Encounters Camp","the first edition of this programme"),
         ("Global Encounters Festival 2025 held","this programme held in 2025"),
         ("Global Encounters programme","this programme")]),
 P("Global Encounters Camps",["Global Encounters Camp","Kenya GE Camp","GE Camps","GE Camp"],PROG,aliases=["Global Encounters Camp","GE Camps"],
   subs=[("the long-run GE Camps participation record","this programme's long-run participation record"),
         ("the first Global Encounters Camp","the first edition of this programme")]),
 P("Time Knowledge Nazrana",["Time and Knowledge Nazrana (TKN)","Time and Knowledge Nazrana","TKN"],"this initiative",
   aliases=["Time and Knowledge Nazrana","TKN"]),
 P("Janbai Maternity Home",["Janbai Maternity Home"],PLACE),
 P("AKU health center Arusha",["Arusha"],PLACE,
   aliases=["Aga Khan Health Center Arusha","Aga Khan Health Centre Arusha","AKU health centre Arusha","AKU Health Center, Arusha","Aga Khan University Health Centre Arusha","Arusha"],
   subs=[("a health centre in Arusha, Tanzania","this health centre")]),
]
def rx(t): return re.compile(r"(?<![A-Za-z0-9])"+re.escape(t)+r"(?![A-Za-z0-9])", re.I)
def rxm(t): return re.compile(r"(?<![A-Za-z0-9])(?:the\s+)?"+re.escape(t)+r"(?![A-Za-z0-9])", re.I)  # also swallows a leading "the"
def normK(x): return re.sub(r"[^a-z0-9]+","",x.lower())

qpath = sys.argv[1] if len(sys.argv)>1 else "questions_en.json"
if not os.path.exists(qpath): qpath = "/mnt/user-data/uploads/questions_en.json"
qs = json.load(open(qpath, encoding="utf-8"))["questions"]
out, short = [], []
for pl in PLACES:
    pats = sorted(pl["terms"], key=len, reverse=True)
    findable = pats + [a for a,_ in pl["subs"]]
    items = []
    for q in qs:
        s = sec(q["id"]); text, ans = q["q"], q["a"]
        scope = (not pl["only"]) or s in pl["only"]
        hit = s in pl["sections"] or (scope and any(rx(t).search(text) or rx(t).search(ans) for t in findable))
        if not hit: continue
        g = text
        for a,b in pl["subs"]: g = g.replace(a,b)
        for t in pats: g = rxm(t).sub(pl["generic"], g)
        g = re.sub(r"\b(this (?:institution|place|building|park|award|programme|network|hotel|museum|organisation)),? this \w+\b", r"\1", g)
        g = g[:1].upper()+g[1:] if g.startswith("this ") else g
        g = re.sub(r"(?<=[.?!] )this ", "This ", g)
        leak = any(rx(t).search(g) for t in pats)
        circ = any(rx(t).search(ans) for t in pats) or normK(ans) in [normK(t) for t in pats]
        items.append(dict(id=q["id"], section=s, q=g, a=ans, original=text, reveals=bool(circ or leak)))
    out.append(dict(name=pl["name"], aliases=sorted(set(pl["aliases"])), generic=pl["generic"], questions=items))
    clean = sum(not i["reveals"] for i in items)
    if clean < 3: short.append((pl["name"], len(items), clean))

def folder_names(arg):
    if os.path.isdir(arg):
        return sorted(d for d in os.listdir(arg) if os.path.isdir(os.path.join(arg, d)))
    if os.path.isfile(arg):   # a manifest.js
        txt = open(arg, encoding="utf-8").read()
        return [x["name"] for x in json.loads(txt[txt.index("["):txt.rindex("]")+1])]
    return []
if len(sys.argv)>2:   # match real picture folders (or manifest.js names) to places
    keys = {}
    for pl in out:
        for k in [pl["name"]]+pl["aliases"]: keys.setdefault(normK(k), pl)
    print("\nPicture folder check:")
    for d in folder_names(sys.argv[2]):
        k = normK(d)
        if k in keys: print(f"  OK       '{d}' -> '{keys[k]['name']}' ({len(keys[k]['questions'])} questions)"); continue
        m = difflib.get_close_matches(k, list(keys), n=1, cutoff=0.75)
        if m:
            keys[m[0]]["aliases"].append(d); keys[k] = keys[m[0]]
            print(f"  ALIASED  '{d}' -> '{keys[m[0]]['name']}' ({len(keys[m[0]]['questions'])} questions)")
        else: print(f"  NO MATCH '{d}'  <- add it to PLACES")

data = dict(places=out)
json.dump(data, open("pictorial.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
open("pictorial.js","w",encoding="utf-8").write("window.IVQ_PICTORIAL = "+json.dumps(data, ensure_ascii=False)+";\n")
print(f"\n{len(out)} places written. Places with fewer than 3 clean questions (name, total, clean):")
for s in short: print("  ", s)
print("\nQuestions per place:", {p['name']: len(p['questions']) for p in out})
