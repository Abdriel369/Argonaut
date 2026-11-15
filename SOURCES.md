# Threshold Sources

> **Prototype using simulated data. This is not a medical diagnostic tool.**

This document explains, threshold by threshold, where each number in `laptop3-orquestador/reglas/config/umbrales.toml` comes from. Each block in that file has a `fuente` field that summarizes the same information and points to references [F1] through [F10] here.

## Rules for this document

1. **Do not invent citations, numbers, pages, or links. Do not cite from memory.** A source counts only if the document was opened and the relevant passage was checked. If it could not be opened, it does not count as verified.
2. **Accepted sources:** NASA standards and documents, peer-reviewed scientific articles, space-agency guidance (ESA, CSA, JAXA), and medical-society clinical guidelines.
3. **For each source, record:** authors, title, journal or publisher, year, DOI or URL, access date, and license, if stated.
4. **Do not reproduce copyrighted articles.** Include only one short quotation in quotation marks with its reference; paraphrase the rest. Each source in this document has one quotation of fewer than 15 words.
5. **Do not store copyrighted article PDFs in the repository.** Store only the reference and link.
6. **If a number does not appear explicitly in a source, do not attribute it to that source.** Write: “principle supported by [source]; cutoff is an original design choice.”
7. **Cutoffs are design decisions.** A cutoff such as “1 hour below the sleep baseline = yellow” does not appear in any standard or article. The source supports the rationale; the team chose the number as an example value. No cutoff in `umbrales.toml` is copied from a source.

## How each source was checked

| Level | Meaning | Sources |
|---|---|---|
| **Verified by the team** | A team member opened the document and confirmed the information | [F1], requirement [V1 4030] only |
| **Checked by the assistant** | The assistant opened the document on 2026-11-15 using a web-reading tool and found the passage. The passage appeared the same in at least two independent readings | [F1] (other requirements), [F2]–[F9] |
| **Abstract only** | Only the abstract could be opened, not the article. **Does not count as verified** | [F10] |
| **Not opened** | Located, but could not be opened. **Does not count** | List at the end |

The reading tool returns text in sections. Before presenting a quotation to the judges, a person should open the link and confirm the passage directly. Each reference identifies the exact information to look for.

## Summary

Of the 18 blocks in `umbrales.toml`:

- **1** has a limit verified by the team (cumulative dose; its cutoffs are design steps).
- **14** have a rationale supported by an opened and checked source. Their cutoffs are original design choices.
- **3** are still marked `SOURCE TO BE CITED`: resting heart rate, heart-rate variability, and the CARDIOVASCULAR rule.

Apart from the 600 mSv limit, only two cases have a number in the source that matches a value in the prototype: the exercise plan of 2 hours per day ([F4]) and the 3-point oxygen-saturation drop ([F8], with qualifications). The 2-day adaptation period falls within the 2-to-3-day range in [F7]. In all other cases, the source supports the rationale, not the number.

## Status of each threshold

| `umbrales.toml` block | Example values | Source | What the source says | What is original design |
|---|---|---|---|---|
| `contexto.dosis_acumulada` | 50 / 150 / 250 mSv | [F1] [V1 4030], **verified by the team** | Career dose below 600 mSv | The three cutoffs: warning steps toward that limit |
| `general` (adaptation) | 2 days, thresholds ×1.5 | [F7] | Space motion sickness generally lasts 2–3 days in flight | The 2-day value and 1.5 multiplier |
| `indicadores.sueno_h` | 1 / 2.5 / 3.5 h below baseline; 3 days | [F2] | Adults should sleep 7 hours or more per night | All cutoffs and duration |
| `indicadores.animo` | 2 / 3 points below baseline; 3 days | [F9] | Prolonged confinement affects behavioral health, differently for each person | Scale, cutoffs, and duration |
| `indicadores.estres` | 20 / 35 / 55 points above baseline; 4 days | [F9] | Same as above | 0–100 scale, cutoffs, and duration |
| `indicadores.ejercicio_min` | 30% / 50% below plan; 5 days | [F4], [F1] [V1 4024] and [V1 4027] | About two hours of exercise per day; maintain muscle strength and bone density | Percentages and duration |
| `indicadores.fc_reposo` | +15% / +25% / +40% | **SOURCE TO BE CITED** (candidate [F10]) | No verified source | Everything |
| `indicadores.hrv` | −20% / −35% / −50% | **SOURCE TO BE CITED** (candidate [F10]) | No verified source | Everything |
| `indicadores.spo2` | 3 / 5 / 8 points below baseline | [F8] | Target range 94–98%; assess after a sudden drop of more than 3% | The 5- and 8-point cutoffs; the 3-point cutoff is supported by the guideline with qualifications |
| `indicadores.temperatura` | +0.8 / +1.3 / +2.0 °C | [F3] | Resting core body temperature rises by about 1 °C during long missions | All three cutoffs |
| `indicadores.ingesta_pct` | below 75% of plan | [F1] [V1 4020], [F5] | Provide 100% of nutritional needs; observed mean intake was 74% | The 75% cutoff |
| `indicadores.tasa_dosis_usv_h` | 60 / 200 / 1000 µSv/h | [F6], [F1] [V1 4031] | Up to 647 µSv/day inside the ISS; protection against solar events | All three cutoffs |
| `combinaciones.FATIGA` | sleep −0.4 h for 3 days, stress +20, exercise 120%, mood −2 | [F2], [F9] | Sleeping less than 7 hours is associated with worse performance and more errors | The combination and its values |
| `combinaciones.AISLAMIENTO` | mood declining for 4 days, cohesion 2.5 or lower | [F9] | Depressive symptoms and conflicts during prolonged confinement | The combination and its values |
| `combinaciones.PERDIDA_MUSCULAR_OSEA` | below 50% of plan, 3 and 5 days | [F1] [V1 4024] and [V1 4027], [F4] | Maintain strength and bone; average bone-density loss of 1% per month | Percentages and duration |
| `combinaciones.RADIACION` | rate 200 µSv/h, heart rate +10%, temperature +0.8 °C | [F1] [V1 4031], [F6] | Protect crew from solar particle events | All values |
| `combinaciones.CARDIOVASCULAR` | heart rate +15%, HRV −20%, sleep −1 h | **SOURCE TO BE CITED** (candidate [F10]) | No verified source | Everything |
| `combinaciones.ENERGIA_BAJA` | below 60% of plan, 2 days | [F1] [V1 4020], [F5] | Same as food intake; Apollo mean was 64% | The 60% cutoff and duration |

The sensor-validation limits (`laptop1-backend-frontend/backend/config/sensores.toml`) are example values without a source. They are explained in `laptop1-backend-frontend/SUPUESTOS.md`.

## References

Access date for all references: **2026-11-15**.

### [F1] NASA-STD-3001 Volume 1, Revision C

- **Authors:** National Aeronautics and Space Administration (NASA).
- **Title:** NASA-STD-3001, Volume 1, Revision C (Crew Health).
- **Publisher:** NASA, published on standards.nasa.gov.
- **Year:** 2023 (approved 2023-09-15).
- **URL:** https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf
- **License:** The document does not specify one.
- **How it was checked:** [V1 4030] verified by the team. The assistant read the other requirements in three readings of the PDF, in the body and in the appendix requirements matrix.
- **Passages** (one short excerpt quoted; the rest paraphrased):
  - [V1 4030], section 4.8.2: total career effective dose from space radiation “shall be less than 600 mSv.” This is based on a 3% REID cancer-mortality risk.
  - [V1 4031], section 4.8.3: the program must protect the crew from the design reference solar particle event, below an effective dose of 250 mSv.
  - [V1 4020], section 4.5.2: provide each crew member with 100% of their calculated nutrient and energy requirements.
  - [V1 4024], section 4.6.2: countermeasures must maintain skeletal muscle strength at 80% or more of baseline.
  - [V1 4027], section 4.7.2: maintain hip and spine bone mineral density at 95% or more of the pre-mission value.
- **What it does not support:** any prototype cutoff. The limit applies to career exposure, while the prototype compares it with the dose in a simulated mission. The 250 mSv in [V1 4031] is a dose from a solar event; although numerically equal to the red cumulative-dose cutoff, it measures something different and does not justify that cutoff.

Cumulative-dose warning steps within the 600 mSv limit: yellow 50 mSv (8%), orange 150 mSv (25%), red 250 mSv (42%). These are internal design steps intended to provide early warnings.

### [F2] AASM/SRS consensus on sleep duration

- **Authors:** Watson NF, Badr MS, Belenky G, Bliwise DL, Buxton OM, Buysse D, Dinges DF, Gangwisch J, Grandner MA, Kushida C, Malhotra RK, Martin JL, Patel SR, Quan SF, Tasali E.
- **Title:** Recommended Amount of Sleep for a Healthy Adult: A Joint Consensus Statement of the American Academy of Sleep Medicine and Sleep Research Society.
- **Journal:** Journal of Clinical Sleep Medicine 11(6):591–592. Also published in Sleep 38(6):843–844.
- **Year:** 2015.
- **DOI:** 10.5664/jcsm.4758 (J Clin Sleep Med); 10.5665/sleep.4716 (Sleep).
- **URL opened:** https://www.aasm.org/resources/pdf/adultsleepdurationconsensus.pdf
- **License:** The PDF does not specify one. It is treated as copyrighted material.
- **Passage:** “Adults should sleep 7 or more hours per night on a regular basis.” The consensus also states that sleeping fewer than 7 hours is associated with poorer performance, more errors, and a higher risk of accidents.
- **What it supports:** insufficient sleep as a performance risk. The profile's sleep baseline (7.2 h) is above the 7-hour recommendation.
- **What it does not support:** the cutoffs of 1, 2.5, and 3.5 hours below baseline, or the persistence period.

### [F3] Body temperature during long-duration space missions

- **Authors:** Stahn AC, Werner A, Opatz O, Maggioni MA, Steinach M, von Ahlefeld VW, Moore A, Crucian BE, Smith SM, Zwart SR, Schlabs T, Mendt S, Trippel T, Koralewski E, Koch J, Choukèr A, Reitz G, Shang P, Röcker L, Kirsch KA, Gunga HC.
- **Title:** Increased core body temperature in astronauts during long-duration space missions.
- **Journal:** Scientific Reports 7:16180.
- **Year:** 2017.
- **DOI:** 10.1038/s41598-017-15560-w. **URL opened:** https://pmc.ncbi.nlm.nih.gov/articles/PMC5701078
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0).
- **Passage:** “At rest CBT was increased by about 1.01 °C on the ISS.” The increase developed gradually over about two and a half months.
- **What it supports:** body temperature changes in space and is worth monitoring.
- **What it does not support:** the +0.8, +1.3, and +2.0 °C cutoffs.
- **Design note:** according to this study, a healthy astronaut on a long-duration mission may be close to 1 °C above their Earth-based value. With the current cutoffs, that would trigger yellow even without illness. The prototype simulates 7 days and recalibrates the baseline only on days 1 and 2; a long mission would require periodic recalibration of the temperature baseline.

### [F4] Exercise on the International Space Station (Canadian Space Agency)

- **Author and publisher:** Canadian Space Agency (CSA), Government of Canada.
- **Title:** Physical activity in space.
- **Year:** Web page; stated modification date: 2025-12-03.
- **URL:** https://www.asc-csa.gc.ca/eng/astronauts/living-in-space/physical-activity-in-space.asp
- **License:** No open license is specified. Its terms (https://www.asc-csa.gc.ca/eng/terms.asp) allow reproduction for non-commercial personal, educational, or informational use with attribution to the CSA.
- **Passage:** “astronauts must exercise approximately two hours per day.” The page also says that, despite exercising, astronauts lose an average of 1% of bone density per month.
- **What it supports:** the exercise plan of 120 minutes per day (`plan.ejercicio_min` in `perfil.toml`). This number does appear in the source.
- **What it does not support:** the 30% and 50% below-plan cutoffs, or their duration.

### [F5] Nutrition during spaceflight (NASA)

- **Authors:** Smith SM, Zwart SR (NASA Johnson Space Center; Universities Space Research Association).
- **Title:** Nutrition issues for space exploration.
- **Publisher:** NASA Technical Reports Server, document 20060049121.
- **Year:** No date is stated in the PDF.
- **URL:** https://ntrs.nasa.gov/api/citations/20060049121/downloads/20060049121.pdf
- **License:** The PDF does not specify one.
- **Passage:** The mean energy intake of 15 ISS crew members “was 74 ± 11% of the WHO recommendation.” The document also reports a mean of 64 ± 14% on Apollo missions and says some ISS crews maintained 85–95%.
- **What it supports:** eating less than planned is common during spaceflight and is a concern.
- **What it does not support:** the 75% and 60% cutoffs. The source figures are observed averages, not alert thresholds. Their proximity to the prototype cutoffs is coincidental, not a justification.

### [F6] Radiation measured inside the International Space Station

- **Authors:** Berger T, Burmeister S, Matthiä D, Przybyla B, Reitz G, Bilski P, Hajek M, Sihver L, Szabo J, Ambrozova I, Vanhavere F, Gaza R, Semones E, Yukihara EG, Benton ER, Uchihori Y, Kodaira S, Kitamura H, Boehme M.
- **Title:** DOSIS & DOSIS 3D: radiation measurements with the DOSTEL instruments onboard the Columbus Laboratory of the ISS in the years 2009–2016.
- **Journal:** Journal of Space Weather and Space Climate 7:A8.
- **Year:** 2017.
- **DOI:** 10.1051/swsc/2017005. **URL opened:** https://www.swsc-journal.org/10.1051/swsc/2017005
- **License:** Creative Commons Attribution 4.0 (CC BY 4.0).
- **Passage:** At the end of May 2016, the absorbed dose reached 286 µGy/day, “with dose equivalent values of 647 μSv/day”.
- **What it supports:** the order of magnitude of the usual rate. 647 µSv/day is about 27 µSv/h (the division by 24 is our calculation, not the source's). The simulated scenario uses 21 µSv/h.
- **What it does not support:** the 60, 200, and 1000 µSv/h cutoffs.

### [F7] Adaptation to microgravity (NASA)

- **Authors:** Wood SJ, Reschke MF, Harm DL, Paloski WH, Bloomberg JJ.
- **Title:** Which Way is Up? Lessons Learned from Space Shuttle Sensorimotor Research.
- **Publisher:** NASA Technical Reports Server, document 20110016709 (document type: abstract).
- **Year:** 2011.
- **URL:** https://ntrs.nasa.gov/citations/20110016709
- **License:** The NASA record indicates that public use is permitted.
- **Passage:** “SMS generally lasted 2-3 days in-flight” (SMS: space motion sickness).
- **What it supports:** the body is adapting during the first days, so a more tolerant approach may be appropriate.
- **What it does not support:** the exact value of 2 days or the 1.5 multiplier. The source gives a 2-to-3-day range for one specific symptom; the prototype selected 2 days for all indicators.

### [F8] Oxygen saturation (British Thoracic Society)

- **Authors:** British Thoracic Society. The document cites the full guideline as: O'Driscoll BR et al., Thorax 2017; 72: Suppl 1 i1–i89.
- **Title:** BTS Guideline for oxygen use in adults in healthcare and emergency settings. Web Appendix 5: Summary of Guideline and flow charts for emergency oxygen use in ambulances, community and pre-hospital settings.
- **Publisher:** British Thoracic Society.
- **Year:** 2017 (May).
- **URL:** https://brit-thoracic.org.uk/document-library/guidelines/emergency-oxygen/web-appendix-5-summary-for-ambulance-and-prehospital-settings
- **License:** The document does not specify one. It is treated as copyrighted material.
- **Passage:** The target saturation range for most patients is 94–98%. “A sudden reduction of more than 3% in a patient's oxygen saturation” within the target range calls for further assessment.
- **What it supports:** the yellow cutoff of 3 points below baseline, with two qualifications: the guideline says “more than 3%” while the prototype uses “3 points or more”; and the guideline concerns patients in healthcare settings, not healthy astronauts.
- **What it does not support:** the 5- and 8-point cutoffs.

### [F9] Behavioral health during prolonged confinement (Mars-500)

- **Authors:** Basner M, Dinges DF, Mollicone DJ, Savelev I, Ecker AJ, Di Antonio A, Jones CW, Hyder EC, Kan K, Morukov BV, Sutton JP.
- **Title:** Psychological and Behavioral Changes during Confinement in a 520-Day Simulated Interplanetary Mission to Mars.
- **Journal:** PLoS ONE 9(3):e93298.
- **Year:** 2014.
- **DOI:** 10.1371/journal.pone.0093298 (https://doi.org/10.1371/journal.pone.0093298).
- **License:** Creative Commons Attribution (CC BY), © 2014 Basner et al.
- **How it was checked:** The publisher and PubMed Central pages did not open with the tool. The journal PDF was read from a third-party copy (https://www.dawsoncollege.qc.ca/writing/wp-content/uploads/sites/196/Article-Mission-to-Mars.pdf); the CC BY license permits that copy. It should be confirmed through the DOI link.
- **Passage:** “Behavioral health risks are among the most serious and difficult to mitigate risks” of long-duration confinement. One crew member experienced depressive symptoms in 93% of weeks, and conflicts with mission control were reported five times more often than among other crew members.
- **What it supports:** monitoring mood, stress, and team relationships, on an individual basis.
- **What it does not support:** any prototype scale or cutoff. It is a ground-based simulation with 6 people.

### [F10] Autonomic control during long-duration spaceflight — ABSTRACT ONLY, NOT VERIFIED

- **Authors:** Baevsky RM, Baranov VM, Funtova II, Diedrich A, Pashenko AV, Chernikova AG, Drescher J, Jordan J, Tank J.
- **Title:** Autonomic cardiovascular and respiratory control during prolonged spaceflights aboard the International Space Station.
- **Journal:** Journal of Applied Physiology 103(1):156–161. American Physiological Society.
- **Year:** 2007.
- **DOI:** 10.1152/japplphysiol.00137.2007.
- **URL opened:** https://edoc.mdc-berlin.de/id/eprint/9190/ (institutional repository record with abstract).
- **License:** The record marks it as closed access. Copyrighted.
- **Abstract passage:** “Impaired autonomic control represents a cardiovascular risk factor during long-term spaceflight”. The abstract also says mean heart rate and variability did not change during flight.
- **Why it does not count:** the article itself could not be opened, only its abstract. It remains a candidate source for heart rate, heart-rate variability, and the CARDIOVASCULAR rule.

## Sources located but not opened (do not count)

| Source | Potential use | What happened |
|---|---|---|
| Barger LK et al. Prevalence of sleep deficiency and use of hypnotic drugs in astronauts before, during, and after spaceflight. Lancet Neurol 2014;13(9):904–912. DOI 10.1016/S1474-4422(14)70122-X | Actual astronaut sleep duration during flight | PubMed Central requested anti-bot verification. The text was visible only in search results |
| Task Force ESC/NASPE. Heart rate variability: standards of measurement, physiological interpretation, and clinical use. Circulation 1996;93(5):1043–1065. DOI 10.1161/01.CIR.93.5.1043 | Heart-rate variability | Could not be opened on the journal site. PubMed has no abstract |
| O'Grady NP et al. SCCM and IDSA Guidelines for Evaluating New Fever in Adult Patients in the ICU. Crit Care Med 2023;51(11):1570–1586. DOI 10.1097/CCM.0000000000006022 | Clinical definition of fever | The PubMed abstract opened, but the fever-defining figure is not in the abstract |
| Petersen N et al. Exercise in space: the European Space Agency approach to in-flight exercise countermeasures. Extrem Physiol Med 2016;5:9. DOI 10.1186/s13728-016-0050-4 (CC BY 4.0) | ESA exercise duration | The publisher page redirects and the tool did not follow it |
| O'Driscoll BR, Howard LS, Earis J, Mak V. BTS Guideline for oxygen use (summary). BMJ Open Respir Res 2017;4:e000170. DOI 10.1136/bmjresp-2016-000170 | Oxygen saturation | Did not open. The society's appendix [F8] was used instead |
| Smith SM et al. The nutritional status of astronauts is altered after long-term space flight aboard the ISS. J Nutr 2005;135(3):437–443. DOI 10.1093/jn/135.3.437 | Energy intake | Could not be opened. [F5] was used instead |
| NASA Human Research Program risk page on sleep loss, circadian misalignment, and workload | Sleep and fatigue | Only the title was checked |
| American Heart Association page on resting heart rate | Resting heart rate | The tool could not open the link |

## What was searched for but not found

- **Sleep hours and exercise minutes in the NASA standard.** NASA-STD-3001 Vol. 1 Rev. C has no requirement specifying sleep hours. In Vol. 2 Rev. F, sections 7.4 (physiological countermeasures) and 7.9 (behavioral health and sleep) do not specify hours or minutes. Only the index and those two sections of Volume 2 were read. Link: https://standards.nasa.gov/system/files/tmp/NASA-STD-3001%20Vol%202%20Rev%20F.pdf
- **Heart rate, heart-rate variability, and body temperature in the standard.** Vol. 1 Rev. C has no requirements with numerical values for these indicators.
- **Documents not opened:** Human Integration Design Handbook, Human Research Program evidence reports, section 6.8 (radiation) of Volume 2, and ESA and JAXA pages.

## How to add or confirm a source

1. Open the actual document and locate the statement. If it cannot be opened, it does not count.
2. Add a `### [Fn]` reference here with authors, title, journal or publisher, year, DOI or URL, access date, license, and one short quotation.
3. Update the `fuente` field in the relevant block in `umbrales.toml`. If the threshold number does not appear explicitly in the source, write “principle supported by [Fn]; cutoff is an original design choice.”
4. Update `PENDIENTES` in `laptop3-orquestador/reglas/pruebas/test_reglas.py`. The tests check that every reference cited in `umbrales.toml` exists here with its link and access date.
5. Do not store copyrighted article PDFs in the repository.
