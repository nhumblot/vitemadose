import json
from scraper.pattern.scraper_request import ScraperRequest
from scraper.pattern.center_location import CenterLocation
from scraper.pattern.center_info import CenterInfo
import httpx
from pathlib import Path
from jsonschema import validate
from jsonschema.exceptions import ValidationError
from datetime import datetime
from dateutil.tz import tzutc
import io
import scraper.mesoigner.mesoigner as mesoigner
from scraper.pattern.vaccine import Vaccine


TEST_CENTRE_INFO = Path("tests", "fixtures", "mesoigner", "mesoigner_center_info.json")


def test_get_appointments():

    """get_appointments should return first available appointment date"""

    center_data = dict()
    center_data = json.load(io.open(TEST_CENTRE_INFO, "r", encoding="utf-8-sig"))

    # This center has availabilities and should return a date, non null appointment_count and vaccines
    request = ScraperRequest(
        "https://pharmacie-des-pyrenees.pharmaxv.fr/rendez-vous/vaccination/269-vaccination-covid-19/pre-inscription",
        "2021-06-16",
        center_data,
    )
    center_with_availability = mesoigner.MesoignerSlots()
    slots = json.load(
        io.open(Path("tests", "fixtures", "mesoigner", "slots_available.json"), "r", encoding="utf-8-sig")
    )
    assert center_with_availability.get_appointments(request, slots_api=slots) == "2021-06-16T14:50:00+02:00"
    assert request.appointment_count == 4
    assert request.vaccine_type == [Vaccine.MODERNA, Vaccine.ASTRAZENECA]

    # This one should return no date, neither appointment_count nor vaccine.
    request = ScraperRequest(
        "https://pharmacie-des-pyrenees.pharmaxv.fr/rendez-vous/vaccination/269-vaccination-covid-19/pre-inscription",
        "2021-07-16",
        center_data,
    )
    center_without_availability = mesoigner.MesoignerSlots()
    slots = json.load(
        io.open(Path("tests", "fixtures", "mesoigner", "slots_unavailable.json"), "r", encoding="utf-8-sig")
    )
    assert center_without_availability.get_appointments(request, slots_api=slots) == None
    assert request.appointment_count == 0
    assert request.vaccine_type == None


from unittest.mock import patch

# On se place dans le cas où la plateforme est désactivée
def test_fetch_slots():
    mesoigner.MESOIGNER_ENABLED = False
    center_data = dict()
    center_data = json.load(io.open(TEST_CENTRE_INFO, "r", encoding="utf-8-sig"))

    request = ScraperRequest(
        "https://pharmacie-des-pyrenees.pharmaxv.fr/rendez-vous/vaccination/269-vaccination-covid-19/pre-inscription",
        "2021-06-16",
        center_data,
    )
    response = mesoigner.fetch_slots(request)

    # On devrait trouver None puisque la plateforme est désactivée
    assert response == None


def test__fetch_slots():
    mesoigner.MESOIGNER_ENABLED = True

    center_data = dict()
    center_data = json.load(io.open(TEST_CENTRE_INFO, "r", encoding="utf-8-sig"))

    center_info = CenterInfo.from_csv_data(center_data)

    # This center has availabilities and should return a date, non null appointment_count and vaccines
    request = ScraperRequest(
        "https://pharmacie-des-pyrenees.pharmaxv.fr/rendez-vous/vaccination/269-vaccination-covid-19/pre-inscription",
        "2021-06-16",
        center_info,
    )
    slots = json.load(
        io.open(Path("tests", "fixtures", "mesoigner", "slots_available.json"), "r", encoding="utf-8-sig")
    )

    def app(requested: httpx.Request) -> httpx.Response:
        assert "User-Agent" in requested.headers

        return httpx.Response(200, json=slots)

    client = httpx.Client(transport=httpx.MockTransport(app))

    center_with_availability = mesoigner.MesoignerSlots(client=client)

    response = center_with_availability._fetch(request)
    assert response == "2021-06-16T14:50:00+02:00"


# def test_center_iterator():
#     def app(request: httpx.Request) -> httpx.Response:
#         if request.url.path == "/api/Organizations/public/covid":
#             path = Path("tests/fixtures/avecmondoc/iterator_search_result.json")
#             return httpx.Response(200, json=json.loads(path.read_text(encoding="utf8")))
#         elif request.url.path == "/api/Organizations/slug/delphine-rousseau-159":
#             path = Path("tests/fixtures/avecmondoc/get_organization_slug.json")
#             return httpx.Response(200, json=json.loads(path.read_text(encoding="utf8")))
#         elif request.url.path == "/api/Organizations/getConsultationReasons":
#             path = Path("tests/fixtures/avecmondoc/get_reasons.json")
#             return httpx.Response(200, json=json.loads(path.read_text(encoding="utf8")))
#         elif request.url.path == "/api/Organizations/getByDoctor/216":
#             path = Path("tests/fixtures/avecmondoc/get_by_doctor.json")
#             return httpx.Response(200, json=json.loads(path.read_text(encoding="utf8")))
#         return httpx.Response(404)

#     client = httpx.Client(transport=httpx.MockTransport(app))
#     centres = [centre for centre in avecmondoc.center_iterator(client)]
#     assert len(centres) > 0
#     data_file = Path("tests/fixtures/avecmondoc/centerdict.json")
#     data = json.loads(data_file.read_text(encoding="utf8"))
#     assert centres[0] == data
