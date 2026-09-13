import pytest
from google.genai import errors
from services import retry


def api_error(code, details=None):
    return errors.APIError(code, {'error': {'code': code, 'message': 'private payload', 'details': details or []}})


@pytest.fixture
def clock(monkeypatch):
    now, waits = [0.0], []
    monkeypatch.setattr(retry.time, 'monotonic', lambda: now[0])
    def sleep(delay):
        waits.append(delay)
        now[0] += delay
    monkeypatch.setattr(retry.time, 'sleep', sleep)
    monkeypatch.setattr(retry.random, 'uniform', lambda *_: 0.5)
    return now, waits


def test_recovers_after_three_temporary_failures(clock, caplog):
    calls = []
    def operation(timeout):
        calls.append(timeout)
        if len(calls) < 4:
            raise api_error(503)
        return 'answer'
    assert retry.call_with_retry(operation, label='answer') == 'answer'
    assert len(calls) == 4
    assert clock[1] == [1.5, 2.5, 4.5]
    assert 'private payload' not in caplog.text


@pytest.mark.parametrize('code', [400, 401, 403, 404])
def test_permanent_errors_do_not_retry(clock, code):
    with pytest.raises(errors.APIError):
        retry.call_with_retry(lambda _: (_ for _ in ()).throw(api_error(code)), label='research')
    assert clock[1] == []


def test_provider_retry_info_is_honored(clock):
    calls = []
    def operation(_):
        calls.append(1)
        if len(calls) == 1:
            raise api_error(429, [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '12s'}])
        return 'ok'
    assert retry.call_with_retry(operation, label='research') == 'ok'
    assert clock[1] == [12]


def test_429_retries_then_returns_success(clock):
    calls = []

    def operation(_):
        calls.append(1)
        if len(calls) < 2:
            raise api_error(429)
        return 'ok'

    assert retry.call_with_retry(operation, label='answer') == 'ok'
    assert len(calls) == 2
    assert clock[1] == [1.5]


def test_long_provider_delay_does_not_sleep_past_deadline(clock):
    with retry.request_budget(10), pytest.raises(errors.APIError):
        retry.call_with_retry(lambda _: (_ for _ in ()).throw(api_error(429, [
            {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '60s'}
        ])), label='research')
    assert clock[1] == []


def test_shared_deadline_caps_next_stage_and_resets(clock):
    with retry.request_budget(5):
        clock[0][0] = 4
        assert retry.call_with_retry(lambda timeout: timeout, label='answer') == 1000
        clock[0][0] = 6
        with pytest.raises(TimeoutError):
            retry.call_with_retry(lambda _: 'should not run', label='answer')
    assert retry.call_with_retry(lambda timeout: timeout, label='new_request') == 40000


def test_exhaustion_stops_at_six_attempts(clock):
    calls = []
    def operation(_):
        calls.append(1)
        raise api_error(503)
    with pytest.raises(errors.APIError):
        retry.call_with_retry(operation, label='research')
    assert len(calls) == 4
    assert len(clock[1]) == 3
