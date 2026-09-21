# Every cited source, read for the value it is cited for

This repository borrows eleven numbers and one fitting form from the literature, and
before this check none of the sources behind them had been opened. The check opened each
one. Two of the three identifiers that earlier work could not expand were resolved first,
`PMC10576773` through the NCBI PMC identifier converter and then Crossref, and
`US 9,445,165` from its patent record; the third, `Ghent pub_4030`, did not resolve. For
each source the fullest open text available was then fetched — the author's arXiv PDF, the
PubMed Central full text, or the patent's own description — and four independent readers
went through it, one for numbers and tables, one for figures, one for equations and
assumptions, and one for the argument, before their findings were reconciled against each
other and against the source. The files themselves are not distributed here, because
some of them may not be: two of the three arXiv PDFs carry a licence that grants
distribution to arXiv alone. Every one of them is listed in
`docs/citation_check/SOURCES.csv` with its URL, its size and its SHA-256, so a reader who
disagrees with a judgement below can fetch the same bytes and check them. Each citation is then one of four things. **supported** means the source states
the value, or one it reasonably rounds to, for the same quantity. **related** means the
source concerns that quantity but gives a different value, or gives the value for a
different structure, platform or band than the one the model uses, so it does not
establish the parameter. **not relevant** means the source does not concern the quantity
at all. **not accessible** means no text beyond an abstract could be obtained and the
abstract does not settle it. No model value, parameter, threshold or assertion was changed
by this check. What changed is what this repository says about where its parameters came
from.

## The table

| Parameter | Value in the code | Source | Classification | Location in the source | Quotation |
|---|---|---|---|---|---|
| `PROP_LOSS_DB_CM` | 2.0 dB/cm | Ochiai, T., et al. *Ultrahigh-sensitivity optical power monitor for Si photonic circuits.* arXiv:2111.01792, 2021; doi 10.1038/s41467-022-35206-4 | related: the value is measured on a boron-doped Si **rib** waveguide, 400 nm wide with a 150 nm rib height in a 300 nm device layer, at **1305 nm** | Supplementary Section III, "Propagation loss of the Si waveguide", PDF page 26 (supplementary page 6); annotated on Fig. S5c | "the propagation loss of the Si waveguide ... extracted to be 2.14 dB/cm" |
| `PROP_LOSS_DB_CM` | 2.0 dB/cm | Baehr-Jones, T., et al. *A 25 Gb/s Silicon Photonics Platform.* arXiv:1203.0767, 2012 | related: the quoted 2.2 ± 0.8 dB/cm is the **rib** average; the same paragraph gives the fully etched channel guide, which is what this model is, as 2.4 ± 0.3 dB/cm | page 4, section 3.1 "Waveguides" | "For channel waveguides with 0.5 µm dimensions, losses of 2.4±0.3 dB/cm were obtained" |
| `PROP_LOSS_DB_CM` | 2.0 dB/cm | Xie, Y., et al. *Towards large-scale programmable silicon photonic chip for signal processing.* Nanophotonics 13(12), 2051–2073, 2024; doi 10.1515/nanoph-2023-0836 | supported | §2.1 "Silicon photonic waveguides", first paragraph, describing the SOI strip waveguide of Fig. 1(a), 0.45 µm × 220 nm | "typically a propagation loss of ∼2 dB/cm" |
| `DC_EXCESS_LOSS_DB` | 0.1 dB per coupler | Gupta, R. K., Chandran, S. and Das, B. K. *Wavelength-Independent Directional Couplers for Integrated Silicon Photonics.* Journal of Lightwave Technology 35(22), 4916–4923, 2017; doi 10.1109/JLT.2017.2759162 | related: the source gives about 0.8 dB, the top of the range the repository quotes and eight times the value used | abstract; no full text is open, so nothing below the abstract could be read | "The average excess loss of such directional couplers is evaluated as ~0.8 dB" |
| `GRATING_PEAK_LOSS_DB` | 4.4 dB | Baehr-Jones, T., et al. arXiv:1203.0767, 2012 | supported; the source calls it an average across 19 dies rather than a peak, and gives ± 0.2 dB, which the repository drops | page 4, section 3.1 "Waveguides" | "The average grating coupler insertion loss across 19 dies was determined to be 4.4±0.2 dB" |
| `GRATING_BW_1P5DB_NM` | 45.0 nm | Baehr-Jones, T., et al. arXiv:1203.0767, 2012 | supported; the decibel level matches exactly | page 4, section 3.1 "Waveguides" | "a typical 1.5 dB bandwidth of 45 nm" |
| `GRATING_LAMBDA_PEAK_NM` | 1545 nm | Baehr-Jones, T., et al. arXiv:1203.0767, 2012 | supported | page 4, section 3.1 "Waveguides" | "with a peak wavelength near 1545 nm" |
| coupler dispersion, the claim that power coupling drifts with wavelength; no constant takes its value from here | κ quoted as 0.60 → 0.82 over 1500–1600 nm at a 100 nm gap | Moss, D. J. *Sagnac interference in integrated photonics for reflection mirrors, gyroscopes, filters, and wavelength interleavers.* Applied Physics Reviews 10, 011309, 2023; arXiv:2302.13177; doi 10.1063/5.0123236 | related: those are the source's numbers exactly, but its κ is the **field** coupling coefficient, under t² + κ² = 1; as power coupling the same figures give about 0.36 → 0.67 | pages 17–18, beside Fig. 8(c-ii); κ defined at page 16, Eq. (8) and page 6, Eq. (1) | "For a gap width of 100 nm, the κ varies from ~0.599 to ~0.820" |
| grating-coupler 1-dB bandwidth; no constant takes its value from here | 38 nm | Korček, R., et al. *Library of single-etch silicon nitride grating couplers for low-loss and fabrication-robust fiber-chip interconnection.* Scientific Reports 13, 17467, 2023; doi 10.1038/s41598-023-44824-x | related: the figure is a simulated value for a **silicon nitride** coupler on a 400 nm LPCVD Si₃N₄ layer, cited in a sentence about silicon couplers on 220 nm silicon-on-insulator | "Design methodology and simulations", the subwavelength-grating paragraph describing Fig. 4(a) | "SWG-based grating coupler ... having a 1-dB bandwidth of 38 nm" |
| the coupled-mode-theory fitting form; no constant takes its value from here | K(λ) = A sin²(k′(λ)L + φ₀) | Dorin, B. and Ye, W. N. *System and method for an optical coupler.* US patent 9,445,165 B2, FutureWei Technologies Inc., granted 13 September 2016 | related: the patent states sin² of a wavelength-dependent coupling phase times a length, which gives the cited kernel in one step, but carries no free amplitude and no constant offset inside the sine, and never names coupled-mode theory | the unnumbered coupling-ratio equation in the detailed description, in the paragraph describing FIG. 8 | "The coupling ratio is not just a function of wavelength, but is given by" |
| the same fitting form | K(λ) = A sin²(k′(λ)L + φ₀) | Ghent `pub_4030` | not accessible: the identifier does not resolve, so no text of any kind could be obtained | — | — |

Four citations are supported, six are related, none is not relevant, and one is not
accessible.

## What did not resolve

`Ghent pub_4030` is cited twice in this repository, in the `coupler.py` module docstring
and in the first reproduction report, both times for the coupled-mode-theory fitting form.
Two attempts were made. The identifier was looked up at the institution the context names,
and `biblio.ugent.be/publication/4030` returns 404 as a page and as JSON. One search was
then built from the citing sentence and put to Crossref; it returned 264,289 matches whose
leader scored 41.4 against a runner-up at 37.8, and none of the records returned was a
Ghent University publication on that fitting form. No record was accepted and nothing has
been written around the identifier. Both attempts, with the query each used, are listed
with the rest of the sources in `docs/citation_check/SOURCES.csv`.

## What the check changes, and what it does not

It changes nothing a model computes. Every constant holds the value it held before, and
the test suite that pins those values is unchanged. What it changes is the standing of the
sources behind four of them.

The one parameter left without a verified source is `DC_EXCESS_LOSS_DB`. Its single
citation now reads `related`: the source it names gives about 0.8 dB where the code uses
0.1 dB. The repository's own summary of that source, "directional-coupler excess loss
~0.1–0.8 dB", quoted a range whose lower end the source does not state. That parameter
belongs with the values §6.3 already records as having no source, and §7.3 now says so.

Three further things a reader should carry away from the table. The propagation loss
survives, but on one citation of three rather than three: the review states about 2 dB/cm
for exactly the geometry this chip uses, while the two measurement papers turn out to
describe rib waveguides, one of them at 1305 nm. The three grating-coupler values are the
cleanest citations in the repository, all three in one sentence at the decibel level
claimed. And the coupler-dispersion note quotes field coupling coefficients under a power
coupling label, which is an error in the comment, not in the model: the coupler's
dispersion is fitted to the chip's own digitized Figure 4d and takes nothing from that
review.

## How the sources were read

| Source | What was obtained |
|---|---|
| arXiv:2111.01792 | author PDF, 29 pages, main text and supplementary |
| arXiv:1203.0767 | author PDF, 11 pages |
| arXiv:2302.13177 | author PDF, 77 pages |
| nanoph-2023-0836 | PubMed Central full text; the publisher's own PDF endpoint refused the request |
| PMC10576773 | PubMed Central full text |
| US 9,445,165 | the patent's description, from its Google Patents record |
| jlt-35-22-4916 | abstract only. Unpaywall reports the DOI closed, Semantic Scholar has no open PDF, and an arXiv title search returns no preprint. The abstract settles the question, so this citation is classified rather than left unaccessible |
| Ghent pub_4030 | nothing; the identifier does not resolve |

None of these files is carried in this repository. `docs/citation_check/SOURCES.csv` gives
the URL, the byte count and the SHA-256 of each, so the same bytes can be fetched and
checked against what is written above.
