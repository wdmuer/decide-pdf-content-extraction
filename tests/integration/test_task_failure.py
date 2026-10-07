import re

import pytest
from decide_ai_service_base.sparql_config import GRAPHS

from . import tasks

TASK_URI = "http://example.org/test/task/missing-pdf"
DOWNLOAD_FAILED = r"PDF extraction: 0/1 succeeded.*download .*404"

ERROR_MESSAGES = """
SELECT ?message WHERE {
  GRAPH <%s> {
    ?error a <http://mu.semte.ch/vocabularies/ext/ErrorMessage> ;
           <http://purl.org/dc/terms/description> ?message
  }
}
"""


def test_a_pdf_that_cannot_be_downloaded_fails_the_task_and_logs_an_error(pdf_site, stub_llm):
    # pdf_site is requested only so the server runs and answers 404 for the unpublished PDF.
    stub_llm("{}")
    tasks.seed("missing_pdf")

    with pytest.raises(RuntimeError, match=DOWNLOAD_FAILED):
        tasks.run(TASK_URI)

    assert tasks.status(TASK_URI) == tasks.FAILED
    rows = tasks.bindings(ERROR_MESSAGES % GRAPHS["data_containers"])
    assert any(re.search(DOWNLOAD_FAILED, r["message"]["value"]) for r in rows), rows
