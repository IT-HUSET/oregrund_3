# data/

Publik branschreferensdata från Svenskt Trä, hämtad 2026-09-18 via
[Handelssortering (PDF)](https://www.svenskttra.se/siteassets/5-publikationer/pdfer/handelssortering_150.pdf)
och [Dimensioner – TräGuiden](https://www.traguiden.se/om-tra/materialet-tra/sagverksprocessen/sagprocessen/dimensioner/).

- `svensktra_standardlangder_mm.csv` — standard handelslängder för sågat virke: 1800–5400 mm i
  steg om 300 mm. Detta är längdaxeln att använda i artikelregistret för kapoptimeringen.
- `svensktra_standardbredder_mm.csv` — standardbredder vid originalsågning: 75–250 mm.
- `svensktra_standardtjocklekar_mm.csv` — standardtjocklekar vid originalsågning: 19, 22, 32, 38 mm.

**Caveat:** bredd/tjocklek-tabellerna ovan gäller *originalsågat* virke, inte färdiga
regelvirkesdimensioner (t.ex. 45×95, 45×145, 45×220 C24) som faktiskt förekommer i
`../components.xml`. De exakta tvärsnitten i det projektet är egna, verifierade produktionsdata
och bör användas som de är — bredd/tjocklek-CSV:erna här är enbart kompletterande branschreferens,
inte en fullständig lista över regelvirkesdimensioner.

**Vad som saknas (måste mockas, inte tillgängligt öppet):** pris per längdmeter/artikel,
artikelnummer/SKU, leveranstid. Se `../docs/prd.md` §6.
