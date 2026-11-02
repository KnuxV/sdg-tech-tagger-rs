# Credits

This package stands on the work of others. Each source is listed with the
version used, its DOI or address, its licence, and what this package did with
it. `CITATION.cff` gives the same references in machine-readable form. If you
use the package, please cite the sources of the queries you use, not only the
package.

## The R package text2sdg, and its engine

The port reproduces what text2sdg returns and is proven against it.

- **text2sdg 1.1.2.** Wulff, D. U. and Meier, D. S., with Mata, R.
  (contributor). *text2sdg: Detecting UN Sustainable Development Goals in
  Text.* R package, CRAN, 2025-09-08. https://doi.org/10.32614/CRAN.package.text2sdg.
  GPL-3. Source: https://github.com/dwulff/text2sdg.
- Meier, D. S., Mata, R. and Wulff, D. U. (2024). text2sdg: An R Package to
  Monitor Sustainable Development Goals from Text. *The R Journal* 16(1),
  83-96. https://doi.org/10.32614/RJ-2024-005.
- Wulff, D. U., Meier, D. S. and Mata, R. (2024). Using novel data and
  ensemble models to improve automated labeling of Sustainable Development
  Goals. *Sustainability Science* 19(5), 1773-1787.
  https://doi.org/10.1007/s11625-024-01516-3.
- Meier, D. S., Mata, R. and Wulff, D. U. (2021). text2sdg: An R package to
  Monitor Sustainable Development Goals from Text. arXiv:2110.05856.
  https://doi.org/10.48550/arXiv.2110.05856.
- **corpustools 0.5.2.** Welbers, K. and van Atteveldt, W. *corpustools:
  Managing, Querying and Analyzing Tokenized Text.* R package, CRAN,
  2025-07-07. https://doi.org/10.32614/CRAN.package.corpustools. GPL-3.
  text2sdg does its matching through corpustools.

**What was done.** The matching rules of corpustools (how a text is cut into
words, what a query means) and the way text2sdg runs each system were
re-implemented in Rust, from their source code. text2sdg's query tables are
shipped unchanged in `query_tables/`. In `compatible` mode the package
returns what text2sdg 1.1.2 returns; `corrected` mode adds a short list of
corrections, each restoring what a published query says (see `README.md`).
The package contains no R code of text2sdg or corpustools.

## The four SDG query systems

- **Aurora.** Vanderfeesten, M., Otten, R. and Spielberg, E. *Search
  Queries for "Mapping Research Output to the Sustainable Development Goals
  (SDGs)"*. Aurora Universities Network. CC BY 4.0.
  - v5.0 (2020), https://doi.org/10.5281/zenodo.3817445: the version
    text2sdg uses, and so the port. Contributors to v5.0, as its README
    lists them: Alessandro Arienzo, Roberto delle Donne, Ignasi Salvadó
    Estivill, José Luis González Ugarte, Didier Vercueil, Nykohla Strong,
    Eike Spielberg, Felix Schmidt, Linda Hasse, Ane Sesma, Baldvin Zarioh,
    Friedrich Gaigg, René Otten, Nicolien van der Grijp, Yasin Gunes,
    Maurice Vanderfeesten.
  - v5.0.3 (2021), GitHub release
    https://github.com/Aurora-Network-Global/sdg-queries/releases/tag/v5.0.3
    (series DOI https://doi.org/10.5281/zenodo.3817444): the version the
    Web of Science files are written from, as it corrects 12 lines of v5.0
    that had typing errors.
- **Elsevier.** Jayabalasingham, B., Boverhof, R., Agnew, K. and Klein, L.
  (2019). *Identifying research supporting the United Nations Sustainable
  Development Goals.* Mendeley Data, version 1.
  https://doi.org/10.17632/87txkw7khs.1. CC BY 4.0. This package is not
  endorsed by Elsevier.
- **SIRIS.** Duran-Silva, N., Fuster, E., Massucci, F. A. and Quinquillà, A.
  (2019). *A controlled vocabulary defining the semantic perimeter of
  Sustainable Development Goals.* Zenodo, version 1.3.
  https://doi.org/10.5281/zenodo.4118028. CC BY-SA 4.0 (ShareAlike: see
  `LICENSE-DATA.md`). text2sdg's documentation names v1.2; its table matches
  v1.3.
- **Auckland.** University of Auckland. *Auckland Approach SDG search
  queries*, version 2.0 (`uoa_sdg_queries_v_2.0.xlsx`), and *UoA SDG Keyword
  List*, version 1.1, https://www.sdgmapping.auckland.ac.nz/. No licence
  stated by the source. Cited, as the site asks, by: Wang, W., Kang, W. and
  Mu, J. (2023). *Mapping research to the Sustainable Development Goals
  (SDGs).* Research Square, preprint version 2.
  https://doi.org/10.21203/rs.3.rs-2544385/v2. The queries are adapted to
  another syntax, not changed in what they search.

**What was done.** Each system's published queries were translated from
Scopus syntax to Web of Science syntax, one query per system and goal, in
`wos_queries/` (rules in `LICENSE-DATA.md` and `docs/wos-sdg-contract.md`).

## The technology queries

The technology queries are by Kevin Michoud. Their terms draw on the
sources below.

### The simplified query of the Nature Communications paper (`adt/wos/`)

Six groups of advanced digital technologies (artificial intelligence with
big data, Internet of Things, computing infrastructure, blockchain, robotics,
additive manufacturing). The six groups follow the framing of the OECD's
*Going Digital* report: OECD (2019), *Going Digital: Shaping Policies,
Improving Lives*, OECD Publishing, Paris, https://doi.org/10.1787/9789264312012-en.
The sources of the individual terms of this version were not recorded.
Gate v2 below holds 275 of its 283 distinct terms, written the same way,
and gives the sources of each of its terms.

### Gate v2 (`adt/gate_v2/`)

Seven groups, the six above and a group of umbrella terms. Every term is in
`adt/gate_v2/provenance.tsv` with the keys of its sources (column
`sources`); `OWN` marks a term of the author's own. The keys resolve below.
These references were collected from a literature review and several were
read in part or as their abstract only.

| key | reference |
|---|---|
| AIW21 | Samoili, S. et al. (2020, 2021). AI Watch. Defining Artificial Intelligence (1.0 and 2.0). JRC, EUR 30117 EN. https://doi.org/10.2760/382730 |
| AMANI20 | Amani, M. et al. (2020). Google Earth Engine Cloud Computing Platform for Remote Sensing Big Data Applications. IEEE JSTARS. https://doi.org/10.1109/JSTARS.2020.3021052 |
| ANTE21 | Ante, L. (2021). Smart contracts on the blockchain. Telematics and Informatics 57, 101519. https://doi.org/10.1016/j.tele.2020.101519 |
| ANZSRC20 | ABS and Stats NZ (2008, 2020). Australian and New Zealand Standard Research Classification. |
| ATI21 | Izsak, K. et al. (2021). Advanced Technologies for Industry: Methodological report. European Commission, EISMEA. https://doi.org/10.2826/911991 |
| ATWATCH20 | Cattaneo, G., Vanara, F., Massaro, A. (2020). AT Watch: Technology Focus on Cloud Computing. European Commission, EASME. |
| BAO25 | Bao, L., Yang, J., Yang, X., Rong, C. (2025). Bibliometric Analysis of Scientific Publications on Blockchain Research and Applications. arXiv:2504.13387. |
| BIANCHINI26 | Bianchini, S., Geuna, A., Shermatov, F. (2026). Scientific Discovery in the Age of AI and Supercomputing. arXiv:2511.12686. |
| BORNMANN19 | Bornmann, L., Haunschild, R., Scheidsteger, T., Ettl, C. (2019). Quantum technology: a bibliometric analysis of a maturing research field. https://doi.org/10.6084/m9.figshare.9731327.v1 |
| CELIK26 | Celik, H.K. et al. (2026). Additive Manufacturing and Wearable Technology: A Bibliometric Analysis. Biosensors 16(3), 172. https://doi.org/10.3390/bios16030172 |
| CHIROMA24 | Chiroma, H., Hashem, I.A.T., Maray, M. (2024). Bibliometric analysis for artificial intelligence in the internet of medical things. Frontiers in AI 7, 1347815. https://doi.org/10.3389/frai.2024.1347815 |
| CPCG06N10 | Cooperative Patent Classification, G06N 10/00 (quantum computing) and G16Y (IoT), version 2026.08. |
| CSET20 | Dunham, J., Melot, J., Murdick, D. (2020). Identifying the development and application of artificial intelligence in scientific text. arXiv:2002.07143. |
| EPO17 | Ménière, Y., Rudyk, I., Valdes, J. (2017). Patents and the Fourth Industrial Revolution: The inventions behind digital transformation. EPO. |
| EPO20, EPO20A | European Patent Office (2020). Patents and the Fourth Industrial Revolution: The global technology trends enabling the data-driven economy; and its methodology annex. |
| EPO23AM | Cavallo, F. et al. (2023). Innovation trends in additive manufacturing. EPO. |
| ETSIMEC15 | Hu, Y.C. et al. (2015). Mobile Edge Computing: A key technology towards 5G. ETSI White Paper No. 11. |
| EUDD22 | Decision (EU) 2022/2481 establishing the Digital Decade Policy Programme 2030. OJ L 323, 19.12.2022. |
| EUROSTAT22IOT, EUROSTAT23 | Eurostat (2022). Use of Internet of Things in enterprises; Eurostat (2023). Methodological manual for ICT usage and e-commerce in enterprises. https://doi.org/10.2785/636267 |
| GORELICK17 | Gorelick, N. et al. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment. https://doi.org/10.1016/j.rse.2017.06.031 |
| GUBBI13 | Gubbi, J., Buyya, R., Marusic, S., Palaniswami, M. (2013). Internet of Things (IoT): A vision, architectural elements, and future directions. FGCS 29(7). https://doi.org/10.1016/j.future.2013.01.010 |
| HE22 | He, C. et al. (2022). A Scientometric Review on Mapping Research Knowledge for 3D Printing Concrete. Materials 15(14), 4796. https://doi.org/10.3390/ma15144796 |
| HLADCHENKO26 | Hladchenko, M. (2026). Emerging and established topics in drone research. arXiv:2606.03362. |
| ICAO328 | ICAO (2011). Unmanned Aircraft Systems (UAS). Cir 328 AN/190. |
| IFR25 | International Federation of Robotics (2025). World Robotics 2025: Service Robots, chapter 1. |
| ISO20924 | ISO/IEC 20924:2021 Internet of Things, Vocabulary. |
| ISO22739 | ISO 22739:2024 Blockchain and distributed ledger technologies, Vocabulary (read as the FDIS sample). |
| ISO8373 | ISO 8373:2021 Robotics, Vocabulary (read through IFR). |
| ISOASTM52900 | ISO/ASTM 52900:2021 Additive manufacturing, General principles, Fundamentals and vocabulary (read as the sample). |
| ISOTR23188 | ISO/IEC TR 23188:2020 Cloud computing, Edge computing landscape (read as the sample). |
| ITUM2083, ITUM2160 | ITU-R Recommendations M.2083-0 (IMT-2020, 2015) and M.2160-0 (IMT-2030, 2023). |
| ITUY2060 | ITU-T Recommendation Y.2060 (2012), Overview of the Internet of things. |
| KAGERMANN13 | Kagermann, H., Wahlster, W., Helbig, J. (2013). Recommendations for implementing the strategic initiative INDUSTRIE 4.0. acatech. |
| LEZAMA18 | Lezama-Nicolás, R., Rodríguez-Salvador, M., Río-Belver, R., Bildosola, I. (2018). A bibliometric method for assessing technological maturity: the case of additive manufacturing. Scientometrics 117(3), 1425-1452. https://doi.org/10.1007/s11192-018-2941-1 |
| LIANG23 | Liang, C.J., Cheng, M.H. (2023). Trends in Robotics Research in Occupational Safety and Health. IJERPH 20(10), 5904. https://doi.org/10.3390/ijerph20105904 |
| LIU21 | Liu, N., Shapira, P., Yue, X. (2021). Tracking developments in artificial intelligence research: constructing and applying a new search strategy. Scientometrics 126(4), 3153-3192. https://doi.org/10.1007/s11192-021-03868-4 |
| MEINDL21 | Meindl, B., Mendonça, J. (2021). Mapping Industry 4.0 Technologies: From Cyber-Physical Systems to Artificial Intelligence. arXiv:2111.14168. |
| MERIT23 | Menéndez de Medina, M., Nomaler, Ö., Verspagen, B. (2023). Identification of Fourth Industrial Revolution technologies using PATSTAT data. UNU-MERIT WP 2023-023. |
| MMM21 | Martinelli, A., Mina, A., Moggi, M. (2021). The enabling technologies of Industry 4.0. Industrial and Corporate Change 30(1), 161-188. https://doi.org/10.1093/icc/dtaa060 |
| NIST500325 | Iorga, M. et al. (2018). Fog Computing Conceptual Model. NIST SP 500-325. https://doi.org/10.6028/NIST.SP.500-325 |
| NIST800145 | Mell, P., Grance, T. (2011). The NIST Definition of Cloud Computing. NIST SP 800-145. https://doi.org/10.6028/NIST.SP.800-145 |
| NIST800223 | Guo, Y. et al. (2024). High-Performance Computing Security. NIST SP 800-223. |
| NISTIR8202 | Yaga, D., Mell, P., Roby, N., Scarfone, K. (2018). Blockchain Technology Overview. NISTIR 8202. https://doi.org/10.6028/NIST.IR.8202 |
| OECD17, OECD17ICT, OECD18IOT, OECD19 | OECD (2017) The Next Production Revolution; Inaba, T., Squicciarini, M. (2017) ICT: a new taxonomy based on the IPC; OECD (2018) IoT measurement and applications, Digital Economy Papers 271; OECD (2019) Measuring the Digital Transformation. |
| OECD20 | Baruffaldi, S. et al. (2020). Identifying and measuring developments in artificial intelligence. OECD STI Working Papers 2020/05. https://doi.org/10.1787/5f65ff7e-en |
| OECDBC18 | OECD (2018). OECD Blockchain Primer. |
| SAEJ3016 | SAE International (2021). J3016 APR2021: Taxonomy and Definitions for Terms Related to Driving Automation Systems. |
| SEBASTIAN20 | Sebastian, A. et al. (2020). Memory devices and applications for in-memory computing. Nature Nanotechnology. https://doi.org/10.1038/s41565-020-0655-z |
| TANG23 | Tang, L., Zhou, X., Lu, M. (2023). An ensemble approach for research article identification: a case study in artificial intelligence. arXiv:2304.09487. |
| UKIPO13, UKIPO14IOT, UKIPO14BD, UKIPO14Q, UKIPORAS14 | UK Intellectual Property Office (2013, 2014). 3D Printing; The Internet of Things; Big Data; Quantum Technologies; Robotics and Autonomous Systems: patent overviews and search strategies. |
| UNCTAD21 | UNCTAD (2021). Technology and Innovation Report 2021: Catching technological waves. UNCTAD/TIR/2020. |
| WEN24 | Wen, S. et al. (2024). Robotic exoskeleton-assisted walking rehabilitation for stroke patients: a bibliometric analysis. Frontiers in Bioengineering and Biotechnology 12, 1391322. |
| WIPO19 | WIPO (2019). WIPO Technology Trends 2019: Artificial Intelligence, and its background paper. |
| WIPO24 | WIPO (2024). Generative Artificial Intelligence: Patent Landscape Report. https://doi.org/10.34667/tind.49740 |
| WIPOWP30 | Keisner, C.A., Raffo, J., Wunsch-Vincent, S. (2015). Breakthrough technologies: Robotics, innovation and intellectual property. WIPO Economic Research WP 30. |
| XUE23 | Xue, A. et al. (2023). A Bibliometric Analysis of 3D Printing in Personalized Medicine Research. Pharmaceuticals 16(11), 1521. |
| ZHANGTAO21 | Zhang, J., Tao, D. (2021). Empowering Things With Intelligence: A Survey of Artificial Intelligence of Things. IEEE Internet of Things Journal. https://doi.org/10.1109/JIOT.2020.3039359 |

Some source cells name their source by the label of an evidence file of
the literature review rather than by a key. Those labels resolve as
follows.

**Evidence file B (artificial intelligence and big data), 85 cells.** The short names are defined at the
top of that file, copied here:

| label | cells that mention it | meaning, as defined in the evidence file |
|---|---|---|
| Liu+ | 16 | in the final strategy of Liu et al. 2021 (key LIU21) |
| OECD20 | 71 | Baruffaldi et al. 2020, Annex Table C.1; "(italic)" = flagged as general by patent examiners (key OECD20) |
| AIW | 29 | JRC AI Watch keyword table, 2020 and 2021 editions (key AIW21) |
| CSET20 | 22 | Dunham et al. 2020, Table B.1 (key CSET20) |
| Tang23 | 16 | Tang, Zhou and Lu 2023, final regular expression (key TANG23) |
| Tang23pre | 28 | Tang, Zhou and Lu 2023, recall-oriented pre-filter (key TANG23) |
| WIPO19-K1, WIPO19-K2 | 17, 2 | WIPO 2019 background paper, patent keyword lists (key WIPO19) |
| WIPO24 | 8 | WIPO 2024 generative AI report, Lens publication query (key WIPO24) |

**Evidence files C (IoT and computing, 50 cells) and D
(blockchain, robotics and additive manufacturing, 45 cells).** Each label is resolved by the
heading it has in its file, copied as written. The middle column counts
mentions of the label in the source cells, so a cell that names three labels
is counted three times. Every label used was found in its file. Several of
these sources have no key in C.1 (for example C: S11, S12, S22, S25, S32,
S33, S39; D: A8, B5, B7, R7, X5): for them the heading above is the only
record kept.

| label | rows | source, as headed in the evidence file |
|---|---|---|
| C: S1 | 2 | ITU-T Y.2060 (06/2012), Overview of the Internet of things |
| C: S2 | 5 | ISO/IEC 20924:2021, Internet of things (IoT): Vocabulary (edition 2) |
| C: S3 | 10 | NIST SP 800-145 (2011), The NIST Definition of Cloud Computing |
| C: S4 | 2 | NIST SP 500-325 (2018), Fog Computing Conceptual Model |
| C: S5 | 3 | ISO/IEC TR 23188:2020, Cloud computing: Edge computing landscape |
| C: S6 | 1 | ETSI White Paper No. 11 (2015), Mobile Edge Computing: A key technology towards 5G |
| C: S9 | 4 | NIST SP 800-223 (2024), High-Performance Computing Security |
| C: S10 | 1 | Cooperative Patent Classification: G16Y (IoT) and G06N 10/00 (quantum computing) |
| C: S11 | 1 | ISO/IEC 4879:2024, Quantum computing: Vocabulary |
| C: S12 | 1 | NIST SP 1900-202 (2019), Cyber-Physical Systems and Internet of Things |
| C: S13 | 2 | OECD (2018), IoT measurement and applications |
| C: S15 | 4 | EPO (2017), Patents and the Fourth Industrial Revolution: the inventions behind digital transformation |
| C: S16 | 4 | EPO (2020), Patents and the Fourth Industrial Revolution: the global technology trends enabling the data-driven economy (main report) |
| C: S17 | 17 | EPO (2020), Methodology for identifying 4IR technologies in patent data (annex) [key verbatim term lists] |
| C: S18 | 6 | Menéndez de Medina, Nomaler, Verspagen (2023), translation of the EPO queries to SQL for PATSTAT |
| C: S19 | 29 | European Commission, Advanced Technologies for Industry (ATI): Methodological report (2021) |
| C: S20 | 4 | European Commission ATI (2020), AT Watch: Technology Focus on Cloud Computing |
| C: S21 | 5 | UNCTAD (2021), Technology and Innovation Report 2021: Catching technological waves |
| C: S22 | 3 | UNCTAD (2023), Technology and Innovation Report 2023: Opening green windows |
| C: S23 | 1 | OECD, Inaba and Squicciarini (2017), ICT: a new taxonomy based on the IPC ("J tag") |
| C: S24 | 14 | Martinelli, Mina, Moggi (2019 WP; 2021 ICC), enabling technologies of Industry 4.0 |
| C: S25 | 3 | Balland and Boschma (2021), Industry 4.0 technologies in European regions |
| C: S26 | 3 | UK Intellectual Property Office (2014), Eight Great Technologies: The Internet of Things, a patent overview |
| C: S27 | 3 | UK IPO (2014), Eight Great Technologies: Big Data, a patent overview |
| C: S28 | 1 | UK IPO (2014), Eight Great Technologies: Quantum Technologies, a patent overview |
| C: S29 | 1 | Bornmann, Haunschild, Scheidsteger, Ettl (2019), quantum technology bibliometrics (query appendix) |
| C: S31 | 3 | Bianchini, Geuna, Shermatov (2025/2026), AI and supercomputing in science |
| C: S32 | 1 | Ruiz-Rosero et al. (2017), Internet of Things: a scientometric review |
| C: S33 | 2 | Dachyar, Zagloel, Saragih (2019), IoT research 2006-2018 |
| C: S38 | 2 | Gubbi, J., Buyya, R., Marusic, S., Palaniswami, M. (2013). Internet of Things (IoT): A vision, architectural elements, and future directions. Future Generation Computer Systems 29(7). https://doi.org/10.1016/j.future.2013.01.010 . |
| C: S39 | 3 | Al-Fuqaha, A., Guizani, M., Mohammadi, M., Aledhari, M., Ayyash, M. (2015). Internet of Things: A Survey on Enabling Technologies, Protocols, and Applications. IEEE Communications Surveys & Tutorials. https://doi.org/10.1109/COMST.2015.2444095 . |
| C: S40 | 1 | Zhang, J., Tao, D. Empowering Things With Intelligence: A Survey of the Progress, Challenges, and Opportunities in Artificial Intelligence of Things. IEEE Internet of Things Journal. https://doi.org/10.1109/JIOT.2020.3039359 . |
| C: S42 | 1 | Amani, M., et al. (2020). Google Earth Engine Cloud Computing Platform for Remote Sensing Big Data Applications: A Comprehensive Review. IEEE JSTARS. https://doi.org/10.1109/JSTARS.2020.3021052 . |
| D: A1 | 12 | ISO/ASTM 52900:2021 |
| D: A2 | 9 | UK IPO (2013): 3D printing patent overview and search strategy |
| D: A3 | 17 | Lezama-Nicolás et al. (2018): AM queries per ASTM process |
| D: A4 | 3 | EPO (2023): Innovation trends in additive manufacturing |
| D: A5 | 4 | Celik et al. (2026): AM and wearables |
| D: A7 | 1 | Xue et al. (2023): 3D printing in personalized medicine |
| D: A8 | 2 | Gibson, Rosen, Stucker (2015): AM textbook title |
| D: B1 | 3 | NIST IR 8202 (2018) |
| D: B2 | 2 | ISO 22739 (vocabulary), read as ISO/FDIS 22739:2023 sample |
| D: B3 | 4 | OECD Blockchain Primer (2018) |
| D: B4 | 3 | Bao, Yang, Yang, Rong (2025): WoS search string for blockchain |
| D: B5 | 1 | Sharma and Khurana (2021) |
| D: B7 | 2 | García-Corral et al. (2022): cryptocurrency bibliometric |
| D: R1 | 3 | ISO 8373:2021 (robotics vocabulary), read through IFR |
| D: R2 | 6 | International Federation of Robotics (2025) |
| D: R4 | 1 | ICAO Circular 328 (2011) |
| D: R5 | 9 | Keisner, Raffo, Wunsch-Vincent (2015/2016), WIPO |
| D: R6 | 6 | UK IPO (2014): Robotics and Autonomous Systems |
| D: R7 | 1 | Guenat et al. (2022): RAS and the SDGs |
| D: R8 | 2 | Hladchenko (2026): drone research on OpenAlex via BigQuery |
| D: R9 | 8 | Liang and Cheng (2023): robotics in occupational safety |
| D: X1 | 12 | UNCTAD Technology and Innovation Report 2021 |
| D: X2 | 7 | EPO (2017): Patents and the Fourth Industrial Revolution |
| D: X3 | 3 | EPO (2020): Patents and the Fourth Industrial Revolution |
| D: X4 | 10 | EU Advanced Technologies for Industry (ATI): Methodological report (2021) |
| D: X5 | 5 | WIPO World Intellectual Property Report 2015 |
| D: X6 | 1 | WIPO Technology Trends 2019: Artificial Intelligence |

## Libraries

- **tantivy** 0.26.2, Masurel, P. and the tantivy contributors,
  https://github.com/quickwit-oss/tantivy. MIT. The word index of the port.
- **ICU4X `icu_segmenter`** 2.3.0, the ICU4X Project Developers, Unicode,
  Inc., https://github.com/unicode-org/icu4x. Unicode-3.0. Cuts texts into
  words by Unicode rules.
- **PyO3**, **rayon**, **regex**, **Polars**: MIT or Apache-2.0.

Every Rust crate compiled into the extension, with its licence text, is in
`THIRD_PARTY_LICENSES.md`.

## Checksums

`adt/gate_v2/SHA256SUMS` lists the files of gate v2 that this package ships.
The BigQuery statement of gate v2 is not shipped, and its line was removed
from that file; every other line is unchanged.
