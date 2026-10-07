"""Seed tasks and run them the way the service does."""
import pathlib
from collections import defaultdict

from decide_ai_service_base.sparql_config import GRAPHS, JOB_STATUSES
from decide_ai_service_base.task import Task
from decide_ai_service_base.util import write_agent_info
from helpers import query, update
from rdflib import Graph

import src.task

FIXTURES = pathlib.Path(__file__).parent / "fixtures"

SUCCESS = JOB_STATUSES["success"]
FAILED = JOB_STATUSES["failed"]

SERVICE_BASE = "http://lblod.data.gift/id/components/pdf-to-eli/v1.0.0"

# The graph the service's queries read each fixture subject from.
GRAPH_BY_SUBJECT_PREFIX = {
    "http://example.org/test/task/": "jobs",
    "http://example.org/test/container/": "data_containers",
    "http://example.org/test/collection/": "harvest_collections",
    "http://example.org/test/remote/": "remote_objects",
}

INSERT_INTO_GRAPH = "INSERT DATA { GRAPH <%s> { %s } }"

TASK_STATUS = """
SELECT ?status WHERE {
  GRAPH <%s> { <%s> <http://www.w3.org/ns/adms#status> ?status }
}
"""

MANIFESTATIONS = """
SELECT ?manifestation ?predicate WHERE {
  GRAPH <%s> {
    ?manifestation <http://data.europa.eu/eli/ontology#is_exemplified_by> <%s> ;
                   ?predicate ?object
  }
}
"""

EXPRESSIONS = """
PREFIX eli: <http://data.europa.eu/eli/ontology#>
PREFIX epvoc: <https://data.europarl.europa.eu/def/epvoc#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?expression ?content ?language ?work ?title WHERE {
  GRAPH <%s> {
    ?expression eli:is_embodied_by <%s> ;
                epvoc:expressionContent ?content ;
                eli:language ?language ;
                eli:realizes ?work
  }
  OPTIONAL {
    GRAPH <%s> {
      ?statement rdf:subject ?expression ;
                 rdf:predicate eli:title ;
                 rdf:object ?title
    }
  }
}
"""

SHAPE_TARGETS = """
SELECT ?node WHERE {
  GRAPH <%s> {
    <%s> <http://mu.semte.ch/vocabularies/ext/shapeForTargets> ?shape .
    ?shape <http://www.w3.org/ns/shacl#targetNode> ?node
  }
}
"""


def bindings(sparql: str) -> list[dict]:
    return query(sparql, sudo=True)["results"]["bindings"]


def _graph_for(subject: str) -> str:
    for prefix, key in GRAPH_BY_SUBJECT_PREFIX.items():
        if subject.startswith(prefix):
            return key
    raise ValueError(f"no graph for fixture subject {subject}")


def seed(fixture_name: str) -> None:
    buckets = defaultdict(Graph)
    for triple in Graph().parse(FIXTURES / f"{fixture_name}.ttl"):
        buckets[_graph_for(str(triple[0]))].add(triple)

    for key, data in buckets.items():
        update(INSERT_INTO_GRAPH % (GRAPHS[key], data.serialize(format="nt")), sudo=True)


def run(task_uri: str) -> None:
    # Same registration as web.py startup.
    write_agent_info(SERVICE_BASE)
    Task.from_uri(task_uri).execute()


def status(task_uri: str) -> str:
    rows = bindings(TASK_STATUS % (GRAPHS["jobs"], task_uri))
    assert len(rows) == 1, f"expected one status for {task_uri}, got {len(rows)}"
    return rows[0]["status"]["value"]


def manifestations(pdf_url: str) -> dict[str, set[str]]:
    found = defaultdict(set)
    for row in bindings(MANIFESTATIONS % (GRAPHS["manifestations"], pdf_url)):
        found[row["manifestation"]["value"]].add(row["predicate"]["value"])
    return dict(found)


def expressions(manifestation_uri: str) -> list[dict]:
    rows = bindings(EXPRESSIONS % (GRAPHS["expressions"], manifestation_uri, GRAPHS["ai"]))
    return [
        {
            "uri": row["expression"]["value"],
            "content": row["content"]["value"],
            "language": row["language"]["value"],
            "work": row["work"]["value"],
            "title": row.get("title", {}).get("value"),
        }
        for row in rows
    ]


def shape_targets(job_uri: str) -> set[str]:
    return {row["node"]["value"] for row in bindings(SHAPE_TARGETS % (GRAPHS["jobs"], job_uri))}
