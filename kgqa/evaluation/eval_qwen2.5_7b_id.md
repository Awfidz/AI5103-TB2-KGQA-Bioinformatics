# KGQA evaluation - qwen2.5:7b

- Run at: 2026-11-21 18:16
- Knowledge graph: Local rdflib graph (drug_discovery.ttl) (1671 triples)
- Model: `qwen2.5:7b` via Ollama, context 4096 tokens, max 3 SPARQL attempts
- Competency questions: **10/15 correct**, 1 verbose, 2 partial, 2 wrong
- Written answers: **11/15** state every expected item (or the right Yes/No); 15/15 in the question's language
- Total time: 764s

List questions: recall = share of the gold query's expected values found in the app's result rows.
Yes/no questions (CQ03-CQ05): scored on whether the written answer says yes or no.
Answer mentions: share of the expected names that appear in the written answer (1.00 = all).
Verdict: *correct* = recall 1 and at most ~2x the expected rows; *verbose* = recall 1 but many more rows
(e.g. duplicated combinations); *partial* = some expected values missing; *wrong* = none found.
Written answers are not scored automatically - see the details section.

## Competency questions

| ID | Question | Verdict | Score | Answer mentions | Language | Rows | Expected values | Attempts | Time (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CQ01 | Lembaga regulator apa saja yang telah menyetujui sildenafil, beserta tanggal persetujuannya? | correct | recall 1.00 | 1.00 | ok | 2 | 2 | 1 | 20.0 |
| CQ02 | Target biologis berupa kompleks multi-protein apa saja yang ditargetkan oleh diazepam atau omeprazole, beserta pengenal UniProt protein penyusunnya? | verbose | recall 1.00 | 1.00 | ok | 11 | 4 | 1 | 54.8 |
| CQ03 | Seorang pasien datang dengan Alcohol withdrawal syndrome, tetapi saat diperiksa masih dalam kondisi Alcohol intoxication. Apakah diazepam diindikasikan resmi untuk kondisi pertama, namun sekaligus dikontraindikasikan pada kondisi kedua dan tergolong obat berizin dengan risiko keamanan tinggi? | wrong | said false | 0.00 | ok | 1 | 1 | 1 | 68.2 |
| CQ04 | Seorang pasien Typhoid fever dengan riwayat Epilepsy dipertimbangkan diberi ciprofloxacin. Apakah ciprofloxacin diindikasikan resmi untuk Typhoid fever, tetapi dikontraindikasikan pada Epilepsy serta memiliki sinyal efek samping kuat (LLR >= 100) berupa Tendon pain? | correct | said true | 1.00 | ok | 1 | 1 | 1 | 48.7 |
| CQ05 | Trastuzumab adalah obat biologik non-molekul kecil untuk kanker payudara HER2+ yang telah disetujui regulator dan memiliki sinyal efek samping kuat (Ejection fraction decreased). Apakah trastuzumab tergolong obat berizin dengan risiko keamanan tinggi (memiliki kontraindikasi sekaligus sinyal efek samping kuat)? | correct | said false | 1.00 | ok | 1 | 1 | 1 | 42.6 |
| CQ06 | Seorang pasien Diabetes mellitus type 2 sedang dirawat karena Acute infectious disease. Obat molekul kecil berizin dengan risiko keamanan tinggi apa saja yang diindikasikan untuk kondisi pertama namun dikontraindikasikan pada kondisi kedua, beserta berat molekulnya? | wrong | recall 0.00 | 0.00 | ok | 0 | 1 | 2 | 63.5 |
| CQ07 | Seorang pasien Hypercholesterolemia memiliki riwayat Disorder of muscle. Obat berizin dengan risiko keamanan tinggi apa saja yang diindikasikan untuk kondisi pertama, dikontraindikasikan pada kondisi kedua, dan memiliki sinyal efek samping kuat berupa Myalgia? | correct | recall 1.00 | 1.00 | ok | 1 | 1 | 1 | 60.1 |
| CQ08 | Seorang dokter mempertimbangkan terapi off-label untuk pasien Chronic heart failure. Obat berizin yang juga digunakan secara off-label apa saja yang memiliki indikasi resmi untuk Hypertensive disorder sekaligus tercatat digunakan secara off-label untuk Chronic heart failure? | correct | recall 1.00 | 1.00 | ok | 1 | 1 | 1 | 39.4 |
| CQ09 | Jalur biologis manusia (Reactome) apa saja yang dipengaruhi oleh mekanisme kerja imatinib? | correct | recall 1.00 | 1.00 | ok | 8 | 8 | 1 | 21.3 |
| CQ10 | Bagaimana profil keamanan lengkap chloroquine (status risiko, status alih fungsi, kontraindikasi pada Deficiency of glucose-6-phosphate dehydrogenase, serta daftar sinyal efek samping kuatnya) untuk audit terapi pasien Falciparum malaria? | partial | recall 0.75 | 0.75 | ok | 9 | 4 | 1 | 77.4 |
| CQ11 | Obat apa saja yang dikontraindikasikan pada pasien dengan Hepatic failure? | correct | recall 1.00 | 1.00 | ok | 6 | 6 | 1 | 19.3 |
| CQ12 | Apa saja tiga sinyal efek samping terkuat (skor LLR tertinggi) yang dilaporkan untuk diazepam? | correct | recall 1.00 | 1.00 | ok | 3 | 3 | 1 | 19.7 |
| CQ13 | Obat apa saja yang disetujui oleh FDA sebelum tahun 1990, beserta tanggal persetujuannya? | correct | recall 1.00 | 1.00 | ok | 4 | 4 | 1 | 22.9 |
| CQ14 | Obat molekul kecil apa saja yang memenuhi kriteria berat molekul aturan Lipinski (< 500 Da), beserta berat molekulnya? | correct | recall 1.00 | 1.00 | ok | 8 | 8 | 1 | 21.2 |
| CQ15 | Obat berizin dengan risiko keamanan tinggi apa saja yang terdapat dalam knowledge graph, beserta jumlah kontraindikasi dan skor LLR tertingginya? | partial | recall 0.11 | 0.11 | ok | 1 | 9 | 1 | 39.0 |

## Extra questions

| ID | Question | Answer | Rows | Attempts | Time (s) |
| --- | --- | --- | --- | --- | --- |
| X1 typo | What is metfromin indicated for? | Metformin is indicated for diabetes mellitus type 2, treatment refractory type 2 diabetes mellitus, and controlled ovarian stimulation:  - Diabetes mellitus type 2 - Treatment Refractory Type 2 Diabetes Mellitus - Controlled ovarian stimulation | 3 | 1 | 22.9 |
| X2 synonym | Which drugs treat high cholesterol? | The knowledge graph has no information that matches this question. | 0 | 2 | 21.9 |
| X3 Indonesian | Apa saja kontraindikasi dari omeprazole? | Beberapa kontraindikasi dari omeprazole adalah:  - Chronic heart failure - Hepatic failure - Hypomagnesemia | 3 | 1 | 19.0 |
| X4 aggregation | Which drug has the most contraindications? | Imatinib has the most contraindications:  - imatinib (number of contraindications: 6) | 1 | 1 | 21.3 |
| X5 multi-hop | Which drugs act on proteins that participate in GABA receptor activation? | The drug that acts on proteins participating in GABA receptor activation is:  - diazepam | 1 | 1 | 20.1 |
| X6 out of scope | What is the recommended daily dose of metformin? | The knowledge graph has no information that matches this question. | 0 | 2 | 41.0 |

## Details

### CQ01: Lembaga regulator apa saja yang telah menyetujui sildenafil, beserta tanggal persetujuannya?

*correct, recall 1.00 (expected: ema, fda)*

Linked entities: `sildenafil`

Attempt 1 (2 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?agencyName ?approvalDate WHERE {
  res:drug_2441 :hasApproval ?approval .
  ?approval :approvedBy ?agency ; :approvalDate ?approvalDate .
  ?agency rdfs:label ?agencyName .
}
ORDER BY ?approvalDate
LIMIT 200
```

```
agencyName | approvalDate
-----------+-------------
FDA        | 1998-03-27
EMA        | 1998-09-13
```

**Answer:** Beberapa lembaga regulator yang telah menyetujui sildenafil adalah FDA dan EMA:

- FDA (approval date: 1998-03-27)
- EMA (approval date: 1998-09-13)

### CQ02: Target biologis berupa kompleks multi-protein apa saja yang ditargetkan oleh diazepam atau omeprazole, beserta pengenal UniProt protein penyusunnya?

*verbose, recall 1.00 (expected: gaba-a receptor alpha-1/beta-2/gamma-2, gaba-a receptor alpha-2/beta-3/gamma-2, gaba-a receptor alpha-3/beta-3/gamma-2, potassium-transporting atpase)*

Linked entities: `omeprazole`, `diazepam`

Attempt 1 (11 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?targetName ?proteinName ?accession WHERE {
  { 
    ?drug rdfs:label ?drugName ; :targets ?target .
    FILTER(?drug = res:drug_852 || ?drug = res:drug_1990)
    ?target rdfs:label ?targetName ; :hasComponent ?protein .
    ?protein rdfs:label ?proteinName ; :uniprotAccession ?accession .
    FILTER(?targetName != "protein complex target")
  }
  UNION
  {
    ?drug rdfs:label ?drugName ; :targets ?target .
    FILTER(?drug = res:drug_852 || ?drug = res:drug_1990)
    ?target rdfs:label ?targetName ; :hasComponent ?protein .
    ?protein rdfs:label ?proteinName ; :uniprotAccession ?accession .
    FILTER(?targetName = "protein complex target")
  }
}
ORDER BY ?drugName ?targetName
LIMIT 200
```

```
targetName                             | proteinName                                                            | accession
---------------------------------------+------------------------------------------------------------------------+----------
GABA-A receptor alpha-1/beta-2/gamma-2 | Gamma-aminobutyric acid receptor subunit alpha-1 (GABA(A) receptor ... | P14867
GABA-A receptor alpha-1/beta-2/gamma-2 | Gamma-aminobutyric acid receptor subunit gamma-2 (GABA(A) receptor ... | P18507
GABA-A receptor alpha-1/beta-2/gamma-2 | Gamma-aminobutyric acid receptor subunit beta-2 (GABA(A) receptor s... | P47870
GABA-A receptor alpha-2/beta-3/gamma-2 | Gamma-aminobutyric acid receptor subunit gamma-2 (GABA(A) receptor ... | P18507
GABA-A receptor alpha-2/beta-3/gamma-2 | Gamma-aminobutyric acid receptor subunit beta-3 (GABA(A) receptor s... | P28472
GABA-A receptor alpha-2/beta-3/gamma-2 | Gamma-aminobutyric acid receptor subunit alpha-2 (GABA(A) receptor ... | P47869
GABA-A receptor alpha-3/beta-3/gamma-2 | Gamma-aminobutyric acid receptor subunit gamma-2 (GABA(A) receptor ... | P18507
GABA-A receptor alpha-3/beta-3/gamma-2 | Gamma-aminobutyric acid receptor subunit beta-3 (GABA(A) receptor s... | P28472
GABA-A receptor alpha-3/beta-3/gamma-2 | Gamma-aminobutyric acid receptor subunit alpha-3 (GABA(A) receptor ... | P34903
Potassium-transporting ATPase          | Potassium-transporting ATPase alpha chain 1 (EC 7.2.2.19) (Gastric ... | P20648
Potassium-transporting ATPase          | Potassium-transporting ATPase subunit beta (Gastric H(+)/K(+) ATPas... | P51164
```

**Answer:** Berikut adalah beberapa protein yang ditargetkan oleh diazepam atau omeprazole:

- GABA-A receptor alpha-1/beta-2/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit alpha-1 (GABA(A) receptor subunit alpha-1) (GABAAR subunit alpha-1), accession: P14867)
- GABA-A receptor alpha-1/beta-2/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit gamma-2 (GABA(A) receptor subunit gamma-2) (GABAAR subunit gamma-2), accession: P18507)
- GABA-A receptor alpha-1/beta-2/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit beta-2 (GABA(A) receptor subunit beta-2) (GABAAR subunit beta-2), accession: P47870)
- GABA-A receptor alpha-2/beta-3/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit gamma-2 (GABA(A) receptor subunit gamma-2) (GABAAR subunit gamma-2), accession: P18507)
- GABA-A receptor alpha-2/beta-3/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit beta-3 (GABA(A) receptor subunit beta-3) (GABAAR subunit beta-3), accession: P28472)
- GABA-A receptor alpha-2/beta-3/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit alpha-2 (GABA(A) receptor subunit alpha-2) (GABAAR subunit alpha-2), accession: P47869)
- GABA-A receptor alpha-3/beta-3/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit gamma-2 (GABA(A) receptor subunit gamma-2) (GABAAR subunit gamma-2), accession: P18507)
- GABA-A receptor alpha-3/beta-3/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit beta-3 (GABA(A) receptor subunit beta-3) (GABAAR subunit beta-3), accession: P28472)
- GABA-A receptor alpha-3/beta-3/gamma-2 (protein name: Gamma-aminobutyric acid receptor subunit alpha-3 (GABA(A) receptor subunit alpha-3) (GABAAR subunit alpha-3), accession: P34903)
- Potassium-transporting ATPase (protein name: Potassium-transporting ATPase alpha chain 1 (EC 7.2.2.19) (Gastric H(+)/K(+) ATPase subunit alpha) (Proton pump), accession: P20648)
- Potassium-transporting ATPase (protein name: Potassium-transporting ATPase subunit beta (Gastric H(+)/K(+) ATPase subunit beta) (Proton pump beta chain), accession: P51164)

### CQ03: Seorang pasien datang dengan Alcohol withdrawal syndrome, tetapi saat diperiksa masih dalam kondisi Alcohol intoxication. Apakah diazepam diindikasikan resmi untuk kondisi pertama, namun sekaligus dikontraindikasikan pada kondisi kedua dan tergolong obat berizin dengan risiko keamanan tinggi?

*wrong: expected true, answer says false*

Linked entities: `Alcohol withdrawal syndrome`, `Alcohol intoxication`, `diazepam`

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
ASK {
  # Indikasi untuk Alcohol withdrawal syndrome
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication .
  FILTER(LCASE(STR(?drugName)) = "diazepam")
  ?indication a :Indication ; :forDisease/rdfs:label ?indicationDisease .
  FILTER(LCASE(STR(?indicationDisease)) = "alcohol withdrawal syndrome")

  # Kontraindikasi untuk Alcohol intoxication
  ?drug :hasAssociation ?contraindication .
  ?contraindication a :Contraindication ; :forDisease/rdfs:label ?contraindicationDisease .
  FILTER(LCASE(STR(?contraindicationDisease)) = "alcohol intoxication")

  # Izin penggunaan dan risiko keamanan tinggi
  ?drug :hasApproval ?approval .
  ?approval :approvedBy ?agency .
  FILTER(?agency/rdfs:label = "FDA" || ?agency/rdfs:label = "EMA" || ?agency/rdfs:label = "PMDA")
  ?approval :approvalDate ?approvalDate .
  FILTER(?approvalDate < "2023-12-31") # Example date, adjust as needed
  ?drug :hasAdverseSignal ?signal .
  ?signal :llrScore ?llr .
  FILTER(?llr >= 100)
}
```

```
answer
------
no
```

**Answer:** Tidak. Diazepam diindikasikan untuk Alcohol withdrawal syndrome, namun dikontraindikasikan pada Alcohol intoxication, dan tergolong obat berizin dengan risiko keamanan tinggi.

### CQ04: Seorang pasien Typhoid fever dengan riwayat Epilepsy dipertimbangkan diberi ciprofloxacin. Apakah ciprofloxacin diindikasikan resmi untuk Typhoid fever, tetapi dikontraindikasikan pada Epilepsy serta memiliki sinyal efek samping kuat (LLR >= 100) berupa Tendon pain?

*correct: expected true, answer says true*

Linked entities: `Typhoid fever`, `ciprofloxacin`, `Tendon pain`, `Epilepsy`

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
ASK {
  # Indication for Typhoid fever
  res:drug_659 :hasAssociation ?indication .
  ?indication a :Indication ; :forDisease res:disease_21000010 .
  
  # Contraindication for Epilepsy
  res:drug_659 :hasAssociation ?contraindication .
  ?contraindication a :Contraindication ; :forDisease res:disease_21001105 .
  
  # Strong adverse signal for Tendon pain
  res:drug_659 :hasAdverseSignal ?signal .
  ?signal :reportsEvent res:ae_10066371 ; :llrScore ?llr .
  FILTER(?llr >= 100)
}
```

```
answer
------
yes
```

**Answer:** Ya, berdasarkan hasil yang diberikan, ciprofloxacin diindikasikan resmi untuk Typhoid fever, dikontraindikasikan pada Epilepsy, dan memiliki sinyal efek samping kuat berupa tendon pain dengan nilai LLR >= 100.

### CQ05: Trastuzumab adalah obat biologik non-molekul kecil untuk kanker payudara HER2+ yang telah disetujui regulator dan memiliki sinyal efek samping kuat (Ejection fraction decreased). Apakah trastuzumab tergolong obat berizin dengan risiko keamanan tinggi (memiliki kontraindikasi sekaligus sinyal efek samping kuat)?

*correct: expected false, answer says false*

Linked entities: `Ejection fraction decreased`, `trastuzumab`

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
ASK {
  res:drug_4979 :hasApproval ?approval .
  ?approval :approvedBy ?agency .
  ?approval :approvalDate ?approvalDate .
  res:drug_4979 :hasAdverseSignal ?signal .
  ?signal :llrScore ?llr .
  FILTER(?llr >= 100)
  ?signal :reportsEvent res:ae_10050528 .
  res:drug_4979 :hasAssociation ?indication ; :hasAssociation ?contraindication .
  ?indication a :Indication ; :forDisease ?diseaseInd .
  ?contraindication a :Contraindication ; :forDisease ?diseaseCon .
}
```

```
answer
------
no
```

**Answer:** Tidak, karena obat trastuzumab memiliki sinyal efek samping kuat tetapi tidak tercatat memiliki kontraindikasi yang sama dengan efek samping tersebut.

### CQ06: Seorang pasien Diabetes mellitus type 2 sedang dirawat karena Acute infectious disease. Obat molekul kecil berizin dengan risiko keamanan tinggi apa saja yang diindikasikan untuk kondisi pertama namun dikontraindikasikan pada kondisi kedua, beserta berat molekulnya?

*wrong, recall 0.00 (expected: metformin)*

Linked entities: `Acute infectious disease`, `Diabetes mellitus type 2`

Attempt 1 (0 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName ?molecularWeight ?indDiseaseName ?conDiseaseName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?ind ; :hasAssociation ?con ; :molecularWeight ?molecularWeight .
  ?ind a :Indication ; :forDisease ?indDisease .
  ?con a :Contraindication ; :forDisease ?conDisease .
  ?indDisease rdfs:label ?indDiseaseName ; rdf:about "res:disease_21000594" .
  ?conDisease rdfs:label ?conDiseaseName ; rdf:about "res:disease_21000413" .
}
ORDER BY DESC(?molecularWeight)
LIMIT 200
```

Attempt 2 (0 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName ?molecularWeight ?indDiseaseName ?conDiseaseName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?ind ; :hasAssociation ?con ; :molecularWeight ?molecularWeight .
  ?ind a :Indication ; :forDisease ?indDisease .
  ?con a :Contraindication ; :forDisease ?conDisease .
  ?indDisease rdfs:label ?indDiseaseName ; rdf:about "res:disease_21000594" .
  ?conDisease rdfs:label ?conDiseaseName ; rdf:about "res:disease_21000413" .
  ?drug :hasAdverseSignal ?signal .
  ?signal :reportsEvent ?event .
  ?event rdfs:label ?eventName .
}
ORDER BY DESC(?molecularWeight)
LIMIT 200
```

**Answer:** Knowledge graph tidak memiliki informasi yang sesuai dengan pertanyaan ini.

### CQ07: Seorang pasien Hypercholesterolemia memiliki riwayat Disorder of muscle. Obat berizin dengan risiko keamanan tinggi apa saja yang diindikasikan untuk kondisi pertama, dikontraindikasikan pada kondisi kedua, dan memiliki sinyal efek samping kuat berupa Myalgia?

*correct, recall 1.00 (expected: atorvastatin)*

Linked entities: `Hypercholesterolemia`, `Disorder of muscle`, `Myalgia`

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName ?indDiseaseName ?offDiseaseName ?aeName WHERE {
  # Indication for Hypercholesterolemia
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication .
  ?indication a :Indication ; :forDisease ?indDisease .
  ?indDisease rdfs:label ?indDiseaseName .
  FILTER(LCASE(STR(?indDiseaseName)) = "hypercholesterolemia")

  # Contraindication for Disorder of muscle
  ?drug :hasAssociation ?contraindication .
  ?contraindication a :Contraindication ; :forDisease ?offDisease .
  ?offDisease rdfs:label ?offDiseaseName .
  FILTER(LCASE(STR(?offDiseaseName)) = "disorder of muscle")

  # Strong adverse signal for Myalgia
  ?drug :hasAdverseSignal ?signal .
  ?signal :reportsEvent ?ae .
  ?ae rdfs:label ?aeName .
  FILTER(LCASE(STR(?aeName)) = "myalgia")
  ?signal :llrScore ?llr .
  FILTER(?llr >= 100)
}
LIMIT 200
```

```
drugName     | indDiseaseName       | offDiseaseName     | aeName
-------------+----------------------+--------------------+--------
atorvastatin | Hypercholesterolemia | Disorder of muscle | Myalgia
```

**Answer:** Beberapa obat yang diindikasikan untuk Hypercholesterolemia, dikontraindikasikan pada Disorder of muscle, dan memiliki sinyal efek samping kuat berupa Myalgia adalah:

- atorvastatin (ind disease name: Hypercholesterolemia, off disease name: Disorder of muscle, ae name: Myalgia)

### CQ08: Seorang dokter mempertimbangkan terapi off-label untuk pasien Chronic heart failure. Obat berizin yang juga digunakan secara off-label apa saja yang memiliki indikasi resmi untuk Hypertensive disorder sekaligus tercatat digunakan secara off-label untuk Chronic heart failure?

*correct, recall 1.00 (expected: losartan)*

Linked entities: `Chronic heart failure`, `Hypertensive disorder`

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName ?indicationDiseaseName ?offLabelDiseaseName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication ; :hasAssociation ?offLabel .
  ?indication a :Indication ; :forDisease ?indicationDisease .
  ?offLabel a :OffLabelUse ; :forDisease ?offLabelDisease .
  ?indicationDisease rdfs:label ?indicationDiseaseName .
  ?offLabelDisease rdfs:label ?offLabelDiseaseName .
  FILTER(?indicationDisease = res:disease_21001432 && ?offLabelDisease = res:disease_21001578)
}
LIMIT 200
```

```
drugName | indicationDiseaseName | offLabelDiseaseName
---------+-----------------------+----------------------
losartan | Hypertensive disorder | Chronic heart failure
```

**Answer:** Ada satu obat yang digunakan untuk hipertensi dan juga digunakan secara off-label untuk gagal jantung kronis:

- losartan (indication disease name: Hypertensive disorder, off label disease name: Chronic heart failure)

### CQ09: Jalur biologis manusia (Reactome) apa saja yang dipengaruhi oleh mekanisme kerja imatinib?

*correct, recall 1.00 (expected: downstream signal transduction, myogenesis, pip3 activates akt signaling, regulation of actin dynamics for phagocytic cup formation, regulation of kit signaling, role of abl in robo-slit signaling, signaling by pdgf, signaling by scf-kit)*

Linked entities: `imatinib`

Attempt 1 (8 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?pathwayName WHERE {
  res:drug_1423 :targets ?target .
  ?target :hasComponent ?protein .
  ?protein :participatesIn ?pathway .
  ?pathway rdfs:label ?pathwayName .
}
LIMIT 200
```

```
pathwayName
---------------------------------------------------------
PIP3 activates AKT signaling
Downstream signal transduction
Signaling by PDGF
Regulation of actin dynamics for phagocytic cup formation
Role of ABL in ROBO-SLIT signaling
Myogenesis
Signaling by SCF-KIT
Regulation of KIT signaling
```

**Answer:** Beberapa jalur biologis yang dipengaruhi oleh mekanisme kerja imatinib adalah:

- PIP3 activates AKT signaling
- Downstream signal transduction
- Signaling by PDGF
- Regulation of actin dynamics for phagocytic cup formation
- Role of ABL in ROBO-SLIT signaling
- Myogenesis
- Signaling by SCF-KIT
- Regulation of KIT signaling

### CQ10: Bagaimana profil keamanan lengkap chloroquine (status risiko, status alih fungsi, kontraindikasi pada Deficiency of glucose-6-phosphate dehydrogenase, serta daftar sinyal efek samping kuatnya) untuk audit terapi pasien Falciparum malaria?

*partial, recall 0.75 (expected: deficiency of glucose-6-phosphate dehydrogenase, hepatitis, off label use, treatment failure)*

Linked entities: `Deficiency of glucose-6-phosphate dehydrogenase`, `Falciparum malaria`, `chloroquine`, `Plasmodium Falciparum Malaria Prevention`

Attempt 1 (9 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?riskStatus ?offLabelUse ?contraindicationAssoc ?adverseEventName ?llrScore WHERE {
  # Approved drug
  res:drug_607 :hasApproval ?approval .
  
  # Risk status
  ?approval :approvedBy ?agency ; :approvalDate ?approvalDate .
  
  # Off-label use
  res:drug_607 :hasAssociation ?offLabelUseAssoc ; :hasAssociation ?indicationAssoc .
  ?offLabelUseAssoc a :OffLabelUse ; :forDisease ?offLabelUseDisease .
  ?indicationAssoc a :Indication ; :forDisease ?indicationDisease .
  
  # Contraindication for Deficiency of glucose-6-phosphate dehydrogenase
  res:drug_607 :hasAssociation ?contraindicationAssoc .
  ?contraindicationAssoc a :Contraindication ; :forDisease res:disease_21000697 .
  
  # Strong adverse signals
  res:drug_607 :hasAdverseSignal ?adverseSignal .
  ?adverseSignal :reportsEvent ?adverseEvent ; :llrScore ?llrScore .
  FILTER(?llrScore >= 100)
  
  # Labels
  ?adverseEvent rdfs:label ?adverseEventName .
  ?agency rdfs:label ?riskStatus .
  ?offLabelUseDisease rdfs:label ?offLabelUse .
  ?indicationDisease rdfs:label ?indicationDiseaseName .
}
LIMIT 200
```

```
riskStatus | offLabelUse                               | contraindicationAssoc | adverseEventName  | llrScore
-----------+-------------------------------------------+-----------------------+-------------------+---------
FDA        | Hypercalcemia associated with Sarcoidosis | res:assoc_ASSOC037178 | Treatment failure | 179.042
FDA        | Hypercalcemia associated with Sarcoidosis | res:assoc_ASSOC037178 | Off label use     | 161.291
FDA        | Hypercalcemia associated with Sarcoidosis | res:assoc_ASSOC037178 | Hepatitis         | 148.83
FDA        | Porphyria cutanea tarda                   | res:assoc_ASSOC037178 | Treatment failure | 179.042
FDA        | Porphyria cutanea tarda                   | res:assoc_ASSOC037178 | Off label use     | 161.291
FDA        | Porphyria cutanea tarda                   | res:assoc_ASSOC037178 | Hepatitis         | 148.83
FDA        | Vasculitis of the skin                    | res:assoc_ASSOC037178 | Treatment failure | 179.042
FDA        | Vasculitis of the skin                    | res:assoc_ASSOC037178 | Off label use     | 161.291
FDA        | Vasculitis of the skin                    | res:assoc_ASSOC037178 | Hepatitis         | 148.83
```

**Answer:** Berikut ini adalah profil keamanan lengkap chloroquine termasuk status risiko, alih fungsi, kontraindikasi, serta efek samping kuatnya untuk audit terapi pasien malaria falciparum,:

- FDA (off label use: Hypercalcemia associated with Sarcoidosis, adverse event name: Treatment failure, LLR score: 179.042)
- FDA (off label use: Hypercalcemia associated with Sarcoidosis, adverse event name: Off label use, LLR score: 161.291)
- FDA (off label use: Hypercalcemia associated with Sarcoidosis, adverse event name: Hepatitis, LLR score: 148.83)
- FDA (off label use: Porphyria cutanea tarda, adverse event name: Treatment failure, LLR score: 179.042)
- FDA (off label use: Porphyria cutanea tarda, adverse event name: Off label use, LLR score: 161.291)
- FDA (off label use: Porphyria cutanea tarda, adverse event name: Hepatitis, LLR score: 148.83)
- FDA (off label use: Vasculitis of the skin, adverse event name: Treatment failure, LLR score: 179.042)
- FDA (off label use: Vasculitis of the skin, adverse event name: Off label use, LLR score: 161.291)
- FDA (off label use: Vasculitis of the skin, adverse event name: Hepatitis, LLR score: 148.83)

### CQ11: Obat apa saja yang dikontraindikasikan pada pasien dengan Hepatic failure?

*correct, recall 1.00 (expected: atorvastatin, diazepam, imatinib, metformin, omeprazole, sildenafil)*

Linked entities: `Hepatic failure`

Attempt 1 (6 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?association .
  ?association a :Contraindication ; :forDisease res:disease_21002196 .
}
LIMIT 200
```

```
drugName
------------
imatinib
metformin
omeprazole
sildenafil
atorvastatin
diazepam
```

**Answer:** Beberapa obat yang dikontraindikasikan pada pasien dengan hepatic failure adalah:

- imatinib
- metformin
- omeprazole
- sildenafil
- atorvastatin
- diazepam

### CQ12: Apa saja tiga sinyal efek samping terkuat (skor LLR tertinggi) yang dilaporkan untuk diazepam?

*correct, recall 1.00 (expected: completed suicide, drug abuse, toxicity to various agents)*

Linked entities: `diazepam`

Attempt 1 (3 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?eventName ?llr WHERE {
  res:drug_852 :hasAdverseSignal ?signal .
  ?signal :llrScore ?llr ; :reportsEvent ?event .
  ?event rdfs:label ?eventName .
} ORDER BY DESC(?llr)
LIMIT 3
```

```
eventName                  | llr
---------------------------+----------
Drug abuse                 | 10918.615
Toxicity to various agents | 9655.77
Completed suicide          | 3684.357
```

**Answer:** Tiga sinyal efek samping terkuat yang dilaporkan untuk diazepam adalah:

- Drug abuse (LLR: 10918.615)
- Toxicity to various agents (LLR: 9655.77)
- Completed suicide (LLR: 3684.357)

### CQ13: Obat apa saja yang disetujui oleh FDA sebelum tahun 1990, beserta tanggal persetujuannya?

*correct, recall 1.00 (expected: chloroquine, ciprofloxacin, diazepam, omeprazole)*

Linked entities: `FDA`

Attempt 1 (4 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName ?approvalDate WHERE {
  ?drug rdfs:label ?drugName ; :hasApproval ?approval .
  ?approval :approvedBy res:agency_fda ; :approvalDate ?approvalDate .
  FILTER(?approvalDate < "1990-01-01")
}
ORDER BY ?approvalDate
LIMIT 200
```

```
drugName      | approvalDate
--------------+-------------
chloroquine   | 1949-10-31
diazepam      | 1963-11-15
ciprofloxacin | 1987-10-22
omeprazole    | 1989-09-14
```

**Answer:** Berikut beberapa obat yang disetujui oleh FDA sebelum tahun 1990:

- chloroquine (approval date: 1949-10-31)
- diazepam (approval date: 1963-11-15)
- ciprofloxacin (approval date: 1987-10-22)
- omeprazole (approval date: 1989-09-14)

### CQ14: Obat molekul kecil apa saja yang memenuhi kriteria berat molekul aturan Lipinski (< 500 Da), beserta berat molekulnya?

*correct, recall 1.00 (expected: chloroquine, ciprofloxacin, diazepam, imatinib, losartan, metformin, omeprazole, sildenafil)*

Attempt 1 (8 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName ?molecularWeight WHERE {
  ?drug rdfs:label ?drugName ; :molecularWeight ?molecularWeight .
  FILTER(?molecularWeight < 500)
}
ORDER BY ASC(?molecularWeight)
LIMIT 200
```

```
drugName      | molecularWeight
--------------+----------------
metformin     | 129.167
diazepam      | 284.74
chloroquine   | 319.88
ciprofloxacin | 331.347
omeprazole    | 345.42
losartan      | 422.92
sildenafil    | 474.58
imatinib      | 493.615
```

**Answer:** Berikut adalah obat-obatan molekul kecil dengan berat molekul kurang dari 500 Da:

- metformin (molecular weight: 129.167)
- diazepam (molecular weight: 284.74)
- chloroquine (molecular weight: 319.88)
- ciprofloxacin (molecular weight: 331.347)
- omeprazole (molecular weight: 345.42)
- losartan (molecular weight: 422.92)
- sildenafil (molecular weight: 474.58)
- imatinib (molecular weight: 493.615)

### CQ15: Obat berizin dengan risiko keamanan tinggi apa saja yang terdapat dalam knowledge graph, beserta jumlah kontraindikasi dan skor LLR tertingginya?

*partial, recall 0.11 (expected: atorvastatin, chloroquine, ciprofloxacin, diazepam, imatinib, losartan, metformin, omeprazole, sildenafil)*

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?drugName (COUNT(DISTINCT ?contraindication) AS ?numberOfContraindications) ?llrScore WHERE {
  ?drug rdfs:label ?drugName ; :hasAdverseSignal ?signal ; :hasAssociation ?indication ; :hasAssociation ?contraindication .
  ?signal :llrScore ?llrScore .
  FILTER(?llrScore >= 100)
  ?indication a :Contraindication ; :forDisease/rdfs:label ?diseaseName .
  ?contraindication a :Contraindication ; :forDisease/rdfs:label ?diseaseName .
}
GROUP BY ?drugName ?llrScore
ORDER BY DESC(?numberOfContraindications) DESC(?llrScore)
LIMIT 1
```

```
drugName  | numberOfContraindications | llrScore
----------+---------------------------+----------
metformin | 6                         | 44808.792
```

**Answer:** Obat dengan risiko keamanan tinggi yang memiliki banyak kontraindikasi adalah:

- metformin (number of contraindications: 6, LLR score: 44808.792)

### X1 typo: What is metfromin indicated for?

Linked entities: `metformin`

Attempt 1 (3 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?diseaseName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?ind .
  FILTER(LCASE(STR(?drugName)) = "metformin")
  ?ind a :Indication ; :forDisease ?disease .
  ?disease rdfs:label ?diseaseName .
}
LIMIT 200
```

```
diseaseName
---------------------------------------------
Diabetes mellitus type 2
Treatment Refractory Type 2 Diabetes Mellitus
Controlled ovarian stimulation
```

**Answer:** Metformin is indicated for diabetes mellitus type 2, treatment refractory type 2 diabetes mellitus, and controlled ovarian stimulation:

- Diabetes mellitus type 2
- Treatment Refractory Type 2 Diabetes Mellitus
- Controlled ovarian stimulation

### X2 synonym: Which drugs treat high cholesterol?

Attempt 1 (0 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication .
  ?indication a :Indication ; :forDisease/rdfs:label ?_label1 .

  FILTER(LCASE(STR(?_label1)) = "high cholesterol")
}
LIMIT 200
```

Attempt 2 (0 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication .
  ?indication a :Indication ; :forDisease/rdfs:label ?_label1 .

  FILTER(LCASE(STR(?_label1)) = "high cholesterol")
}
LIMIT 200
```

**Answer:** The knowledge graph has no information that matches this question.

### X3 Indonesian: Apa saja kontraindikasi dari omeprazole?

Linked entities: `omeprazole`

Attempt 1 (3 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?diseaseName WHERE {
  res:drug_1990 :hasAssociation ?association .
  ?association a :Contraindication ; :forDisease ?disease .
  ?disease rdfs:label ?diseaseName .
}
LIMIT 200
```

```
diseaseName
---------------------
Chronic heart failure
Hepatic failure
Hypomagnesemia
```

**Answer:** Beberapa kontraindikasi dari omeprazole adalah:

- Chronic heart failure
- Hepatic failure
- Hypomagnesemia

### X4 aggregation: Which drug has the most contraindications?

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?drugName (COUNT(DISTINCT ?ci) AS ?numberOfContraindications) WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?ci .
  ?ci a :Contraindication ; :forDisease ?disease .
}
GROUP BY ?drugName
ORDER BY DESC(?numberOfContraindications)
LIMIT 1
```

```
drugName | numberOfContraindications
---------+--------------------------
imatinib | 6
```

**Answer:** Imatinib has the most contraindications:

- imatinib (number of contraindications: 6)

### X5 multi-hop: Which drugs act on proteins that participate in GABA receptor activation?

Linked entities: `GABA receptor activation`

Attempt 1 (1 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT DISTINCT ?drugName WHERE {
  ?drug rdfs:label ?drugName ; :targets ?target .
  ?target :hasComponent ?protein .
  ?protein :participatesIn ?pathway .
  ?pathway rdfs:label ?_label1 .

  FILTER(LCASE(STR(?_label1)) = "gaba receptor activation")
}
LIMIT 200
```

```
drugName
--------
diazepam
```

**Answer:** The drug that acts on proteins participating in GABA receptor activation is:

- diazepam

### X6 out of scope: What is the recommended daily dose of metformin?

Linked entities: `metformin`

Attempt 1 (0 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?drugName ?dose WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication .
  FILTER(LCASE(STR(?drugName)) = "metformin")
  ?indication a :Indication ; :forDisease ?disease .
  ?approval :approvedBy ?agency ; :forDrug ?drug ; :recommendedDose ?dose .
  ?agency rdfs:label ?agencyName .
}
LIMIT 200
```

Attempt 2 (0 row(s)):

```sparql
PREFIX : <https://itb.ac.id/a5103/tubes_2#>
PREFIX res: <https://itb.ac.id/a5103/tubes_2/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?drugName ?dose WHERE {
  ?drug rdfs:label ?drugName ; :hasAssociation ?indication .
  FILTER(LCASE(STR(?drugName)) = "metformin")
  ?indication a :Indication ; :forDisease ?disease .
  ?approval :approvedBy ?agency ; :forDrug ?drug ; :recommendedDose ?dose .
  ?drug :hasAdverseSignal ?signal .
  ?signal :reportsEvent ?event .
  ?event rdfs:label ?eventName .
  ?agency rdfs:label ?agencyName .
}
LIMIT 200
```

**Answer:** The knowledge graph has no information that matches this question.
