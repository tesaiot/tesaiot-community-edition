# SPDX-License-Identifier: Apache-2.0
# Copyright TESAIoT Platform contributors

"""``to_mongo_dict()`` must work on the pydantic major the image installs.

Both of these model files declare their target in a comment — "Pydantic v1
compatibility - use allow_population_by_field_name instead of v2's
populate_by_name" — and then called ``model_dump()``, which exists only in
pydantic 2. requirements.txt pins 1.10.13, so every call raised
``AttributeError: object has no attribute 'model_dump'`` on a live path: the CSR
workflow tracker (services/api/api/services/csr_workflow_service.py) and the
enhanced device log writer both go through ``to_mongo_dict()`` before inserting.

Nothing caught it. ruff sees a valid attribute access, compileall sees valid
syntax, and CI installed neither pydantic nor the models. These tests import the
real modules and call the real method, so the interpreter answers instead of a
static tool guessing.

They also hold the post-processing contract: ``to_mongo_dict`` converts ISO
strings back to datetimes with ``isinstance(data[field], str)``. If serialisation
ever starts handing that loop strings where it used to hand it datetimes, the
branch silently stops running and Mongo receives strings where the rest of the
code expects datetimes. Asserting the type is what keeps that honest.
"""

import os
import importlib.util
from datetime import datetime

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODELS = os.path.abspath(os.path.join(_HERE, '..', '..', 'api', 'models'))

_FIXED = datetime(2026, 9, 6, 3, 21, 0)


def _load(name, filename):
    path = os.path.join(_MODELS, filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def csr():
    return _load('csr_workflow_status', 'csr_workflow_status.py')


@pytest.fixture(scope='module')
def device_log():
    return _load('device_log_enhanced', 'device_log_enhanced.py')


def test_csr_workflow_serialises(csr):
    """The document Mongo receives for a new CSR workflow."""
    workflow = csr.CSRWorkflowStatusModel(
        device_id='dev-1', correlation_id='corr-1',
        started_at=_FIXED, updated_at=_FIXED,
    )
    doc = workflow.to_mongo_dict()

    assert '_id' in doc, "the id field must serialise under its alias, or Mongo gets a second key"
    assert doc['device_id'] == 'dev-1'
    assert len(doc['steps']) == len(csr.WORKFLOW_STEP_ORDER)


def test_device_log_serialises(device_log):
    """The document Mongo receives for one device log entry."""
    entry = device_log.EnhancedDeviceLog(
        device_id='dev-1', event_type='mqtt_connected',
        message='hello', timestamp=_FIXED,
    )
    doc = entry.to_mongo_dict()

    assert '_id' in doc
    assert doc['event_type'] == 'mqtt_connected'


@pytest.mark.parametrize('field', ['started_at', 'updated_at'])
def test_csr_timestamps_stay_datetimes(csr, field):
    """Not strings: the ISO-string branch in to_mongo_dict exists for a reason."""
    workflow = csr.CSRWorkflowStatusModel(
        device_id='dev-1', correlation_id='corr-1',
        started_at=_FIXED, updated_at=_FIXED,
    )
    assert isinstance(workflow.to_mongo_dict()[field], datetime)


def test_device_log_timestamp_stays_datetime(device_log):
    entry = device_log.EnhancedDeviceLog(
        device_id='dev-1', event_type='mqtt_connected',
        message='hello', timestamp=_FIXED,
    )
    assert isinstance(entry.to_mongo_dict()['timestamp'], datetime)


def test_nested_steps_and_error_serialise(csr):
    """Nested models, None values and an extra field, in one document.

    The equivalence between the v1 and v2 spellings was measured on exactly this
    shape; keeping it here means a future change to either has to survive it.
    """
    workflow = csr.CSRWorkflowStatusModel(
        device_id='dev-1', correlation_id='corr-1',
        started_at=_FIXED, updated_at=_FIXED,
        current_step='csr_submitted',
        steps={
            'mqtt_connected': csr.WorkflowStepDetail(
                status=csr.StepStatus.COMPLETED, timestamp=_FIXED, duration_ms=12),
            'csr_submitted': csr.WorkflowStepDetail(
                status=csr.StepStatus.IN_PROGRESS, details=None),
        },
        error=csr.WorkflowError(
            step='csr_validated', code='E_BAD_CSR', message='bad',
            suggestion=None, timestamp=_FIXED),
        csr_info={'subject': 'CN=dev-1', 'key': None},
    )
    doc = workflow.to_mongo_dict()

    assert doc['steps']['mqtt_connected']['duration_ms'] == 12
    assert 'details' not in doc['steps']['csr_submitted'], "exclude_none must drop it"
    assert doc['error']['code'] == 'E_BAD_CSR'
    assert 'suggestion' not in doc['error']
    assert 'key' not in doc['csr_info'] or doc['csr_info'].get('key') is None
