import json

from . import tasks

HEADER = "Gemeenteraad Gent - zitting van 1 september 2026"
TITLE_1 = "Besluit 1: Aanleg fietspad Kerkstraat"
BODY_1 = "De gemeenteraad keurt de aanleg van een fietspad in de Kerkstraat goed."
TITLE_2 = "Besluit 2: Renovatie stadhuis"
BODY_2 = "De gemeenteraad keurt de renovatie van het stadhuis goed."
NLD = "http://publications.europa.eu/resource/authority/language/NLD"
SKIPPED = "http://mu.semte.ch/vocabularies/ext/skippedDueToPageLimit"

# Line numbers refer to the text Tika extracts, which starts with an empty line.
BOTH_TITLES = json.dumps({
    "document_classification": "Minutes",
    "spans": [
        {"tag": "decision_title", "start_line": 3, "end_line": 3},
        {"tag": "decision_title", "start_line": 5, "end_line": 5},
    ],
})


def test_a_pdf_with_two_decision_titles_becomes_two_expressions(pdf_site, stub_llm):
    stub_llm(BOTH_TITLES)
    url = pdf_site("two-decisions.pdf", [[HEADER, TITLE_1, BODY_1, TITLE_2, BODY_2]])
    task_uri = "http://example.org/test/task/two-decisions"
    tasks.seed("two_decisions")

    tasks.run(task_uri)

    assert tasks.status(task_uri) == tasks.SUCCESS
    manifestations = tasks.manifestations(url)
    assert len(manifestations) == 1, manifestations
    expressions = tasks.expressions(next(iter(manifestations)))
    assert len(expressions) == 2, expressions
    assert {e["language"] for e in expressions} == {NLD}
    assert len({e["work"] for e in expressions}) == 2
    assert {e["title"] for e in expressions} == {TITLE_1, TITLE_2}

    content = {e["title"]: e["content"] for e in expressions}
    assert HEADER in content[TITLE_1] and BODY_1 in content[TITLE_1]
    assert BODY_2 not in content[TITLE_1]
    assert HEADER in content[TITLE_2] and BODY_2 in content[TITLE_2]
    assert BODY_1 not in content[TITLE_2]

    job_uri = "http://example.org/test/job/two-decisions"
    assert tasks.shape_targets(job_uri) == {e["uri"] for e in expressions}


def test_splitting_disabled_keeps_the_document_as_one_expression(pdf_site, stub_llm):
    stub_llm(BOTH_TITLES)
    url = pdf_site("split-disabled.pdf", [[HEADER, TITLE_1, BODY_1, TITLE_2, BODY_2]])
    task_uri = "http://example.org/test/task/split-disabled"
    tasks.seed("split_disabled")

    tasks.run(task_uri)

    assert tasks.status(task_uri) == tasks.SUCCESS
    manifestations = tasks.manifestations(url)
    assert len(manifestations) == 1, manifestations
    expressions = tasks.expressions(next(iter(manifestations)))
    assert len(expressions) == 1, expressions
    assert BODY_1 in expressions[0]["content"] and BODY_2 in expressions[0]["content"]
    assert expressions[0]["title"] == TITLE_1


def test_a_pdf_over_the_page_limit_is_only_recorded_as_skipped(pdf_site, stub_llm):
    stub_llm("{}")
    url = pdf_site("long-pdf.pdf", [[HEADER]] + [[f"Pagina {n}"] for n in range(2, 12)])
    task_uri = "http://example.org/test/task/long-pdf"
    tasks.seed("long_pdf")

    tasks.run(task_uri)

    assert tasks.status(task_uri) == tasks.SUCCESS
    manifestations = tasks.manifestations(url)
    assert len(manifestations) == 1, manifestations
    manifestation_uri, predicates = next(iter(manifestations.items()))
    assert SKIPPED in predicates
    assert tasks.expressions(manifestation_uri) == []
