"""Builds pictorial.json (+ pictorial.js) from questions_en.json.
Edit PLACES below: `name` should match the folder name in /pictures (aliases = other spellings).
A question joins a place if any term appears in its question or answer (inside `only` sections if given),
or if its section is in `sections`. Place terms in the question text are replaced by `generic`."""
import json, re, sys
SEC = {1:(1,15),2:(16,23),3:(24,25),4:(26,44),5:(45,59),6:(60,74),7:(75,89),8:(90,100),9:(101,108),
       10:(109,127),11:(128,169),12:(170,191),13:(192,200),14:(201,243),15:(244,256),16:(257,275)}
def sec(i): return next(s for s,(a,b) in SEC.items() if a<=i<=b)
INST, PLACE, BLD = "this institution", "this place", "this building"
def P(name, terms, generic=PLACE, sections=(), only=(), aliases=()):
    return dict(name=name, terms=list(terms), generic=generic, sections=list(sections), only=list(only), aliases=list(aliases))
PLACES = [
 P("Aga Khan Foundation",["Aga Khan Foundation","AKF"],INST,[8],aliases=["AKF"]),
 P("Aga Khan Agency for Habitat",["Aga Khan Agency for Habitat","AKAH"],INST,[9],aliases=["AKAH"]),
 P("Aga Khan Health Services",["Aga Khan Health Services","Aga Khan Health Service","AKHSP","AKHS"],INST,[10],aliases=["AKHS"]),
 P("Aga Khan University",["Aga Khan University Examination Board","Aga Khan University Hospital, Nairobi","Aga Khan University Hospital","Aga Khan University","AKU-EB","AKU-SONAM","AKUH Karachi","AKUH Nairobi","AKUH","AKU"],INST,[11],aliases=["AKU","Aga Khan University Hospital"]),
 P("Aga Khan Academy",["Aga Khan Academies","Aga Khan Academy Hyderabad - India","Aga Khan Academy Mombasa","Aga Khan Academy Hyderabad","Aga Khan Academy Dhaka","Aga Khan Academy Maputo","Aga Khan Academy"],INST,aliases=["Aga Khan Academies","Aga Khan Academy Mombasa","Aga Khan Academy Hyderabad","Aga Khan Academy Dhaka"]),
 P("Aga Khan Schools",["Aga Khan Schools","Aga Khan Education Services","AKES","AKS"],INST,[12],aliases=["Aga Khan Education Services","AKES"]),
 P("University of Central Asia",["University of Central Asia","UCA"],INST,[13],aliases=["UCA"]),
 P("Aga Khan Trust for Culture",["Aga Khan Trust for Culture","AKTC"],INST,[14],aliases=["AKTC"]),
 P("Aga Khan Agency for Microfinance",["Aga Khan Agency for Microfinance","AKAM","First MicroFinance Bank","FMFB-PAKISTAN","FMFB-Tajikistan","FMFB-A"],INST,[15],aliases=["AKAM"]),
 P("Aga Khan Fund for Economic Development",["Aga Khan Fund for Economic Development","AKFED"],INST,[16],aliases=["AKFED"]),
 P("Institute of Ismaili Studies",["The Institute of Ismaili Studies","Institute of Ismaili Studies","IIS"],INST,[6],aliases=["IIS"]),
 P("Aga Khan Centre",["Aga Khan Centre"],BLD,aliases=["Aga Khan Centre London"]),
 P("Ismaili Centre London",["Ismaili Centre, London","Ismaili Centre London","London"],BLD,only=[4],aliases=["Ismaili Centre, London"]),
 P("Ismaili Centre Burnaby",["Burnaby"],BLD,only=[4],aliases=["Ismaili Centre Vancouver"]),
 P("Ismaili Centre Lisbon",["Ismaili Centre, Lisbon","Ismaili Centre Lisbon","Lisbon"],BLD,only=[4],aliases=["Ismaili Centre, Lisbon"]),
 P("Ismaili Centre Dubai",["Ismaili Centre, Dubai","Ismaili Centre Dubai","Dubai"],BLD,only=[4],aliases=["Ismaili Centre, Dubai"]),
 P("Ismaili Centre Dushanbe",["Ismaili Centre, Dushanbe","Ismaili Centre Dushanbe","Dushanbe"],BLD,only=[4],aliases=["Ismaili Centre, Dushanbe"]),
 P("Ismaili Centre Toronto",["Ismaili Centre, Toronto","Ismaili Centre Toronto","Toronto"],BLD,only=[4],aliases=["Ismaili Centre, Toronto"]),
 P("Ismaili Centre Houston",["Ismaili Centre, Houston","Ismaili Centre Houston","Ismaili Center","Houston"],BLD,only=[4],aliases=["Ismaili Centre, Houston"]),
 P("Diwan of the Ismaili Imamat",["Diwan of the Ismaili Imamat","Seat of the Ismaili Imamat","Seat of Ismaili Imamat","Lisbon"],BLD,only=[1],aliases=["Seat of the Ismaili Imamat","The Diwan"]),
 P("Aga Khan Museum",["Aga Khan Museum in Toronto","Aga Khan Museum"],BLD),
 P("Aga Khan Park",["Aga Khan Park in Toronto","Aga Khan Park"],PLACE),
 P("Al-Azhar Park",["Al-Azhar Park"],PLACE,aliases=["Al Azhar Park"]),
 P("Humayun's Tomb",["Humayun World Heritage Site Museum","Humayun"],PLACE,aliases=["Humayun Tomb","Humayuns Tomb"]),
 P("Baltit Fort",["Baltit Fort"],PLACE),
 P("Altit Fort",["Altit Fort"],PLACE),
 P("Wazir Khan Mosque",["Wazir Khan Mosque"],BLD),
 P("Citadel of Aleppo",["Citadel of Aleppo","Aleppo"],PLACE,aliases=["Aleppo Citadel"]),
 P("Blue Mosque Cairo",["Mosque of Amir Aqsunqur","Blue Mosque"],BLD,aliases=["Mosque of Amir Aqsunqur"]),
 P("Timur Shah Mausoleum",["Timur Shah Mausoleum"],PLACE),
 P("Alamut Castle",["Alamut Castle"],PLACE,aliases=["Alamut"]),
 P("Islamabad Serena Hotel",["Islamabad Serena Hotel"],BLD,aliases=["Serena Islamabad"]),
 P("Dushanbe Serena Hotel",["Dushanbe Serena Hotel"],BLD,aliases=["Serena Dushanbe"]),
 P("Serena Shigar Fort",["Serena Shigar Fort"],PLACE,aliases=["Shigar Fort"]),
 P("Serena Khaplu Palace",["Serena Khaplu Palace"],PLACE,aliases=["Khaplu Palace"]),
 P("HBL",["HBL Microfinance Bank","HBL"],INST,aliases=["Habib Bank Limited","HBL Microfinance Bank"]),
 P("Roshan",["Roshan"],INST),
 P("Pamir Energy",["Pamir Energy"],INST),
 P("Azito Power",["Azito Power"],PLACE,aliases=["Azito"]),
 P("Jubilee Insurance",["Jubilee General Insurance","The Jubilee Insurance Company","Jubilee Insurance Company"],INST,aliases=["Jubilee General Insurance"]),
 P("Diamond Trust Bank",["Diamond Trust Bank","Diamond Jubilee Investment Trust"],INST),
 P("Global Centre for Pluralism",["Global Centre for Pluralism"],BLD,aliases=["Global Center for Pluralism"]),
 P("Janbai Maternity Home",["Janbai Maternity Home"],PLACE),
 P("Aga Khan Medical Centre Gilgit",["Aga Khan Medical Centre, Gilgit"],PLACE,aliases=["Aga Khan Medical Centre, Gilgit"]),
 P("Aga Khan Award for Architecture",["Aga Khan Award for Architecture"],INST),
 P("Aga Khan Music Awards",["Aga Khan Music Awards","Aga Khan Music Award","AKMA"],INST,aliases=["Aga Khan Music Award"]),
 P("Tcell",["Indigo Tajikistan","Tcell"],INST),
 P("Nation Media Group",["Sunday Nation","Daily Nation","Taifa and Nation"],INST,aliases=["Daily Nation"]),
]
def rx(t): return re.compile(r"(?<![A-Za-z0-9])"+re.escape(t)+r"(?![A-Za-z0-9])", re.I)
def rxm(t): return re.compile(r"(?<![A-Za-z0-9])(?:the\s+)?"+re.escape(t)+r"(?![A-Za-z0-9])", re.I)  # also swallows a leading "the"
qs = json.load(open("/mnt/user-data/uploads/questions_en.json", encoding="utf-8"))["questions"]
out, short = [], []
for pl in PLACES:
    pats = sorted(pl["terms"], key=len, reverse=True)
    items = []
    for q in qs:
        s = sec(q["id"]); text, ans = q["q"], q["a"]
        scope = (not pl["only"]) or s in pl["only"]
        hit = s in pl["sections"] or (scope and any(rx(t).search(text) or rx(t).search(ans) for t in pats))
        if not hit: continue
        g = text
        for t in pats: g = rxm(t).sub(pl["generic"], g)
        g = re.sub(r"\b(this (?:institution|place|building)),? (?:this (?:institution|place|building))\b", r"\1", g)
        g = g[:1].upper() + g[1:] if g.startswith("this ") else g
        g = re.sub(r"(?<=[.?!] )this ", "This ", g)
        leak = any(rx(t).search(g) for t in pats)
        circular = any(rx(t).search(ans) for t in pats) or any(re.sub(r"[^a-z]","",ans.lower())==re.sub(r"[^a-z]","",t.lower()) for t in pats)
        items.append(dict(id=q["id"], section=s, q=g, a=ans, original=text, reveals=bool(circular or leak)))
    out.append(dict(name=pl["name"], aliases=pl["aliases"], generic=pl["generic"], questions=items))
    if sum(not i["reveals"] for i in items) < 3: short.append((pl["name"], len(items), sum(not i["reveals"] for i in items)))
data = dict(places=out)
json.dump(data, open("pictorial.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
open("pictorial.js","w",encoding="utf-8").write("window.IVQ_PICTORIAL = "+json.dumps(data, ensure_ascii=False)+";\n")
print(len(out),"places;", sum(len(p["questions"]) for p in out),"question slots")
print("fewer than 3 clean questions (name, total, clean):")
for s in short: print("  ",s)
