import csv

MASTER = r'e:\FASAL_POC_Full\frappe-bench\apps\rythulab\rythulab\sheets\Disease\AP_Disease_CF_MF_Triggers - AP_Disease_CF_MF_Triggers.csv'
NEW    = r'e:\FASAL_POC_Full\frappe-bench\apps\rythulab\rythulab\sheets\Disease\new\AP_Disease_CF_MF_Triggers_filled - AP_Disease_CF_MF_Triggers.csv'

# Load master: name -> DiseaseID
master_rows = []
with open(MASTER, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        master_rows.append({'id': row['DiseaseID'], 'name': row['Disease'].strip()})

# Explicit alias map: normalized new-sheet name -> DiseaseID
ALIASES = {
    'rice blast (pyricularia oryzae)': 'DIS0119',
    'rice sheath blight (rhizoctonia solani)': 'DIS0120',
    'rice bacterial leaf blight (xanthomonas oryzae)': 'DIS0118',
    'rice tungro virus (rtbv/rtsv)': 'DIS0121',
    'rice brown spot (helminthosporium oryzae)': 'DIS0029',
    'rice neck rot (bakanae/fusarium)': 'DIS0101',
    'sorghum downy mildew (peronosclerospora sorghi)': 'DIS0055',
    'sorghum charcoal rot (macrophomina phaseolina)': 'DIS0037',
    'sorghum grain smut (sporisorium sorghi)': 'DIS0071',
    'maize downy mildew (peronosclerospora maydis)': 'DIS0095',
    'maize banded leaf & sheath blight (rhizoctonia solani)': 'DIS0131',
    'wheat rust (puccinia spp.)': 'DIS0125',
    'wheat loose smut (ustilago tritici)': 'DIS0093',
    'pearl millet downy mildew (sclerospora graminicola)': 'DIS0055',
    'pearl millet ergot (claviceps fusiformis)': 'DIS0060',
    'pearl millet smut (moesziomyces penicillariae)': 'DIS0134',
    'finger millet blast (pyricularia grisea)': 'DIS0022',
    'finger millet neck blast (pyricularia grisea)': 'DIS0022',
    'jowar anthracnose (colletotrichum graminicola)': 'DIS0004',
    'foxtail millet smut (ustilago crameri)': 'DIS0134',
    'kodo millet head smut (sorosporium paspali)': 'DIS0080',
    'little millet leaf spot (helminthosporium sp.)': 'DIS0091',
    'barnyard millet blast (pyricularia oryzae)': 'DIS0022',
    'proso millet head smut (sporisorium panici-miliacei)': 'DIS0080',
    'redgram wilt (fusarium udum)': 'DIS0115',
    'redgram sterility mosaic virus': 'DIS0141',
    'redgram phytophthora blight (phytophthora drechsleri)': 'DIS0105',
    'blackgram yellow mosaic virus': 'DIS0154',
    'blackgram web blight (rhizoctonia solani)': 'DIS0086',
    'greengram cercospora leaf spot': 'DIS0036',
    'chickpea wilt (fusarium oxysporum)': 'DIS0069',
    'chickpea botrytis grey mould (botrytis cinerea)': 'DIS0026',
    'chickpea ascochyta blight (ascochyta rabiei)': 'DIS0006',
    'horsegram anthracnose (colletotrichum lindemuthianum)': 'DIS0004',
    'cowpea rust (uromyces vignae)': 'DIS0125',
    'soybean rust (phakopsora pachyrhizi)': 'DIS0125',
    'groundnut tikka leaf spot (cercospora arachidicola)': 'DIS0076',
    'groundnut dry root rot (macrophomina phaseolina)': 'DIS0075',
    'groundnut stem rot (sclerotium rolfsii)': 'DIS0139',
    'groundnut late leaf spot (cercosporidium personatum)': 'DIS0091',
    'sunflower downy mildew (plasmopara halstedii)': 'DIS0055',
    'sunflower alternaria blight (alternaria helianthi)': 'DIS0001',
    'sesame phyllody (phytoplasma)': 'DIS0104',
    'sesame alternaria leaf spot': 'DIS0003',
    'castor botrytis grey mould': 'DIS0026',
    'castor wilt (fusarium oxysporum)': 'DIS0069',
    'rapeseed alternaria blight (alternaria brassicae)': 'DIS0001',
    'linseed rust (melampsora lini)': 'DIS0125',
    'cotton boll rot (fusarium/colletotrichum)': 'DIS0049',
    'cotton leaf curl virus (clcuv)': 'DIS0050',
    'cotton alternaria leaf spot (alternaria macrospora)': 'DIS0003',
    'cotton angular leaf spot (xanthomonas axonopodis)': 'DIS0011',
    'sugarcane red rot (colletotrichum falcatum)': 'DIS0113',
    'sugarcane smut (sporisorium scitamineum)': 'DIS0134',
    'sugarcane grassy shoot phytoplasma': 'DIS0072',
    'tobacco mosaic virus (tmv)': 'DIS0099',
    'tobacco frog eye leaf spot (cercospora nicotianae)': 'DIS0091',
    'chilli leaf curl virus': 'DIS0040',
    'chilli damping off (pythium aphanidermatum)': 'DIS0039',
    'chilli anthracnose (colletotrichum capsici)': 'DIS0004',
    'chilli bacterial wilt (ralstonia solanacearum)': 'DIS0014',
    'turmeric rhizome rot (pythium aphanidermatum)': 'DIS0116',
    'turmeric leaf blotch (taphrina maculans)': 'DIS0087',
    'mango anthracnose (colletotrichum gloeosporioides)': 'DIS0004',
    'mango powdery mildew (oidium mangiferae)': 'DIS0110',
    'mango bacterial canker (xanthomonas campestris)': 'DIS0009',
    'banana sigatoka leaf spot (mycosphaerella musicola)': 'DIS0132',
    'banana panama wilt (fusarium oxysporum f.sp. cubense)': 'DIS0102',
    'banana bunchy top virus (bbtv)': 'DIS0033',
    'citrus canker (xanthomonas axonopodis)': 'DIS0042',
    'citrus greening (huanglongbing - candidatus liberibacter)': 'DIS0073',
    'citrus powdery mildew (oidium tingitaninum)': 'DIS0110',
    'papaya damping off (pythium sp.)': 'DIS0053',
    'papaya mosaic virus (papmv)': 'DIS0099',
    'papaya phytophthora foot rot': 'DIS0061',
    'guava wilt (fusarium oxysporum f.sp. psidii)': 'DIS0069',
    'guava anthracnose (colletotrichum gloeosporioides)': 'DIS0004',
    'sapota leaf spot (pestalotiopsis sapotae)': 'DIS0091',
    'grape downy mildew (plasmopara viticola)': 'DIS0055',
    'grape powdery mildew (erysiphe necator)': 'DIS0110',
    'pomegranate bacterial blight (xanthomonas axonopodis)': 'DIS0008',
    'pomegranate cercospora fruit spot': 'DIS0068',
    'cashew die back (lasiodiplodia theobromae)': 'DIS0054',
    'coconut bud rot (phytophthora palmivora)': 'DIS0032',
    'coconut grey leaf blight (pestalotiopsis palmarum)': 'DIS0086',
    'tomato early blight (alternaria solani)': 'DIS0058',
    'tomato late blight (phytophthora infestans)': 'DIS0085',
    'tomato bacterial wilt (ralstonia solanacearum)': 'DIS0014',
    'tomato leaf curl virus (tolcv)': 'DIS0089',
    'brinjal little leaf phytoplasma': 'DIS0092',
    'brinjal phomopsis blight (phomopsis vexans)': 'DIS0103',
    'brinjal damping off (pythium aphanidermatum)': 'DIS0053',
    'okra yellow vein mosaic (yvmv)': 'DIS0156',
    'okra powdery mildew (erysiphe cichoracearum)': 'DIS0110',
    'cucurbit downy mildew (pseudoperonospora cubensis)': 'DIS0055',
    'cucurbit powdery mildew (podosphaera xanthii)': 'DIS0110',
    'cucurbit mosaic virus (cmv)': 'DIS0099',
    'bitter gourd anthracnose (colletotrichum orbiculare)': 'DIS0004',
    'onion purple blotch (alternaria porri)': 'DIS0111',
    'onion stemphylium leaf blight': 'DIS0140',
    'onion downy mildew (peronospora destructor)': 'DIS0055',
    'potato late blight (phytophthora infestans)': 'DIS0085',
    'potato early blight (alternaria solani)': 'DIS0058',
    'potato bacterial wilt (ralstonia solanacearum)': 'DIS0014',
    'cauliflower black rot (xanthomonas campestris)': 'DIS0019',
    'cauliflower downy mildew (peronospora brassicae)': 'DIS0055',
    'cabbage club root (plasmodiophora brassicae)': 'DIS0043',
    'beans anthracnose (colletotrichum lindemuthianum)': 'DIS0004',
    'beans bean common mosaic virus': 'DIS0099',
    'amaranthus damping off (pythium sp.)': 'DIS0053',
}

# Read new file
with open(NEW, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

matched_ids = set()
unmatched_new = []

for row in rows:
    name = row.get('Disease', '').strip()
    if not name:
        row['DiseaseID'] = ''
        continue
    did = ALIASES.get(name.lower(), '')
    row['DiseaseID'] = did
    if did:
        matched_ids.add(did)
    else:
        unmatched_new.append(name)

new_fields = ['DiseaseID'] + list(fieldnames)
with open(NEW, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=new_fields)
    w.writeheader()
    w.writerows(rows)

non_empty = [r for r in rows if r.get('Disease', '').strip()]
print(f'Total new rows: {len(non_empty)} | Matched: {len(non_empty) - len(unmatched_new)} | Unmatched: {len(unmatched_new)}')
if unmatched_new:
    print('\nUnmatched in new sheet (no DiseaseID assigned):')
    for n in unmatched_new:
        print(f'  - {n}')

not_in_new = [r for r in master_rows if r['id'] not in matched_ids]
print(f'\nMaster diseases NOT present in new sheet ({len(not_in_new)}) — appending:')
for r in not_in_new:
    print(f"  {r['id']}  {r['name']}")

# Append missing master rows to new sheet
master_full = []
with open(MASTER, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        master_full.append(row)

missing_ids = {r['id'] for r in not_in_new}
rows_to_append = [
    {
        'DiseaseID': row['DiseaseID'],
        'Disease': row['Disease'],
        'CF_TriggerIncites': row['CF_TriggerIncites'],
        'MF_IncreasesOccurance': row['MF_IncreasesOccurance'],
        'MF_DecreasesOccurance': row['MF_DecreasesOccurance'],
    }
    for row in master_full if row['DiseaseID'] in missing_ids
]

with open(NEW, 'a', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=new_fields)
    w.writerows(rows_to_append)

print(f'\nAppended {len(rows_to_append)} rows from master to new sheet.')
