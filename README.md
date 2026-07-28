# Horizon Europe DMP (Norway)

The template is based on the official [Template Horizon Europe Data Management Plan (DMP)](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/report/data-management-plan_he_en.docx) designed for use in [Data Stewardship Wizard](https://ds-wizard.org) with the *Norwegian generic knowledge model* (`research.data.no:norway-generic`, 1.2.1 or newer).

It is a fork of the [upstream Horizon Europe DMP template](https://github.com/ds-wizard/horizon-europe-dmp-template) with two changes:

* **Navigation by annotation.** The upstream template addresses the knowledge model through hardcoded question UUIDs. This version navigates by the `json.key` / `json.value` annotations that the Norwegian knowledge model carries, so it contains no UUIDs at all. Which questions appear in which EC section is declared in [`src/_sections.j2`](src/_sections.j2), driven by the knowledge model's *Horizon Europe* tag.
* **Structured answers instead of prose.** The upstream template synthesises English sentences per answer branch. This version keeps the EC section structure and headings but renders each question with its title and its reply, in the style of the *Questionnaire Report - lean* template: markdown values, tables for item lists with fewer than six sub-questions, comma-separated multiple choices, and an explicit placeholder for questions that have not been answered.

Because it relies on `extract_replies`, it requires DSW 4.20 or newer (template metamodel 18.1).


## Development

`tools/` holds a local harness that renders the template without a DSW instance:

```bash
KM=../KM-tooling/mapJsonKeysWF/results/research.data.no_norway-generic_1.2.1-squashed.km

python3 tools/check_syntax.py                              # parse every template
python3 tools/check_sections.py --km $KM --tag "Horizon Europe"   # validate src/_sections.j2
python3 tools/make_test_context.py --km $KM --replies all -o /tmp/ctx.json
python3 tools/render.py --input /tmp/ctx.json --template $PWD/src/index.html.j2 -o /tmp/out.html
```

`make_test_context.py` builds a document context straight from the knowledge model, so the template can be exercised before a real project export exists. Use `--replies none` to check the unanswered-question path. A real export from the DSW instance is still the better final test, and the PDF and Word steps (weasyprint, pandoc) only run in the instance itself.


## Usage

This template is distributed for the Norwegian DSW instance. The upstream template it forks is available through the [DSW Registry](https://registry.ds-wizard.org/templates).


## Issues and Contributing

This document template for DSW is available as open-source via GitHub Repository [DHP-stottepakke/horizon-europe-dmp-template](https://github.com/DHP-stottepakke/horizon-europe-dmp-template), you can [report issues](https://github.com/DHP-stottepakke/horizon-europe-dmp-template/issues) there and fork it for customizations or contributions.

## AI-Assisted Development

Some recent changes in this repository were developed with AI-assisted tooling. Proposed code, template mappings, local tooling, and documentation changes were reviewed and adapted by human contributors before being kept in the repository.

For the work captured in this thread, the following AI tooling was used:

- Agent: Claude Code
- Models: Claude Opus 5

### Contributors

* **Marek Suchánek** <[marek.suchanek@ds-wizard.org](mailto:marek.suchanek@ds-wizard.org)>
  * ORCID: [0000-0001-7525-9218](https://orcid.org/0000-0001-7525-9218)
  * GitHub: [@MarekSuchanek](https://github.com/MarekSuchanek)
* **Kryštof Komanec** <[krystof.komanec@ds-wizard.org](mailto:krystof.komanec@ds-wizard.org)>
  * ORCID: [0000-0003-3856-1682](https://orcid.org/0000-0003-3856-1682)
  * GitHub: [@krystofkomanec](https://github.com/krystofkomanec)
* **Jana Martínková** <[jana.martinkova@ds-wizard.org](mailto:jana.martinkova@ds-wizard.org)>
  * ORCID: [0000-0001-8575-6533](https://orcid.org/0000-0001-8575-6533/)
  * GitHub: [@jmartinkova](https://github.com/jmartinkova)

### Edits

* **Korbinian Bösl** <[korbinian.bosl@uib.no](mailto:korbinian.bosl@uib.no)>
  * ORCID: [0000-0003-0498-4273](https://orcid.org/0000-0003-0498-4273)
  * GitHub: [@korbinib](https://github.com/korbinib)
* **Michael Dondrup** <[mdondrup@gmail.com](mailto:mdondrup@gmail.com)>
  * ORCID: [0000-0002-2371-5928](https://orcid.org/0000-0002-2371-5928)
  * GitHub: [@mdondrup](https://github.com/mdondrup)

## Changelog

### 1.0.0

Initial release of the Norwegian port: new template ID `research.data.no:horizon-europe-dmp-norway`, annotation-based navigation against `research.data.no:norway-generic` 1.2.1+, and lean-style structured answer rendering. Section content is selected by the knowledge model's *Horizon Europe* tag; `src/_sections.j2` records the mapping and `tools/check_sections.py` tests it.
