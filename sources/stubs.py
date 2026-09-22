"""
Sources named in the v1 spec that are not implemented as live
integrations, and why. Each still shows up in the UI's source list
(F2/status transparency) so it's clear what's active vs. pending.

  - LinkedIn: no public jobs API; scraping violates LinkedIn's ToS.
  - Indeed: publisher API was retired; current access is
    partner-only and requires a commercial agreement.
  - Guardian Jobs: the standalone job board was discontinued.
  - cwjobs / Totaljobs / ContractorUK: no public API; each is part
    of a scraping-protected commercial network.
  - efinancialcareers: no public API.

To bring any of these online, add a module here that implements the
same `fetch() -> list[dict]` contract as the live sources in this
package (see sources/base.py's `normalize()` helper), for example
by wiring up a licensed data feed or an official partner API.
"""
from sources.base import StubSource

STUB_SOURCES = [
    StubSource("LinkedIn", "No public jobs API; scraping would violate LinkedIn's Terms of Service"),
    StubSource("Indeed", "Publisher API retired; current access is partner-only"),
    StubSource("Guardian Jobs", "Guardian Jobs board has been discontinued"),
    StubSource("cwjobs", "No public API (StepStone/Totaljobs Group network)"),
    StubSource("Totaljobs", "No public API (StepStone/Totaljobs Group network)"),
    StubSource("ContractorUK", "No public API"),
    StubSource("efinancialcareers", "No public API"),
]
