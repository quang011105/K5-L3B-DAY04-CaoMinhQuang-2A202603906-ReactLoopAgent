"""Offline checks for real Retry-After handling and incident evidence."""
import unittest
from unittest.mock import Mock, patch

from agent import ToolRetryBudget, retry_delay, run_agent
from bonus.tools import BonusTools
from test_agent import ScriptedProvider, call, final


class RetryTests(unittest.TestCase):
    @patch('agent.time.sleep')
    @patch('agent.time.monotonic', return_value=100.0)
    def test_waits_before_retry_and_preserves_observation(self, clock, sleep):
        limited = {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '2'}
        tools = Mock()
        tools.execute.side_effect = [limited, {'provider': 'vercel'}]
        budget, trace = ToolRetryBudget(), []
        self.assertEqual(budget.execute(tools, 'get_vercel_status', {}, trace, 1), limited)
        self.assertEqual(budget.execute(tools, 'get_vercel_status', {}, trace, 2)['provider'], 'vercel')
        sleep.assert_called_once_with(2.0)
        self.assertEqual(trace[0]['event'], 'retry_wait')

    def test_persistent_429_stops_after_three_actual_calls(self):
        tools = Mock()
        tools.execute.return_value = {'ok': False, 'error': 'RATE_LIMITED', 'retry_after_seconds': 0}
        budget = ToolRetryBudget()
        for _ in range(3):
            budget.execute(tools, 'get_vercel_status', {}, [], 1)
        blocked = budget.execute(tools, 'get_incident_details', {'provider': 'vercel'}, [], 2)
        self.assertEqual(blocked['error'], 'RETRY_LIMIT')
        self.assertEqual(tools.execute.call_count, 3)
        tools.execute.return_value = {'provider': 'github'}
        self.assertEqual(budget.execute(tools, 'get_github_status', {}, [], 2)['provider'], 'github')

    @patch('agent.time.sleep')
    def test_long_retry_after_stops_without_early_request(self, sleep):
        tools = Mock()
        tools.execute.return_value = {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '60'}
        budget = ToolRetryBudget()
        budget.execute(tools, 'get_npm_status', {}, [], 1)
        self.assertEqual(budget.execute(tools, 'get_npm_status', {}, [], 2)['error'], 'RETRY_BUDGET_EXCEEDED')
        self.assertEqual(tools.execute.call_count, 1)
        sleep.assert_not_called()

    @patch('agent.time.monotonic', return_value=100.0)
    @patch('agent.time.sleep')
    def test_total_wait_budget(self, sleep, clock):
        tools = Mock()
        tools.execute.return_value = {'ok': False, 'error': 'RATE_LIMITED', 'retry_after': '9'}
        budget = ToolRetryBudget()
        for name in ['get_github_status', 'get_npm_status', 'get_vercel_status']:
            budget.execute(tools, name, {}, [], 1)
            budget.execute(tools, name, {}, [], 2)
        budget.execute(tools, 'get_cloudflare_status', {}, [], 3)
        self.assertEqual(budget.execute(tools, 'get_cloudflare_status', {}, [], 4)['error'], 'RETRY_BUDGET_EXCEEDED')
        self.assertEqual(sleep.call_count, 3)

    @patch('agent.time.time', return_value=0)
    def test_http_date_and_invalid_header(self, clock):
        self.assertEqual(retry_delay({'retry_after': 'Thu, 01 Jan 1970 00:00:05 GMT'}), 5)
        self.assertEqual(retry_delay({'retry_after': 'bad header'}), 2)
        self.assertEqual(retry_delay({'retry_after_seconds': 0}), 0)


class DetailEvidenceTests(unittest.TestCase):
    def test_summary_only_answer_gets_details_revision(self):
        tools = BonusTools()
        status = tools.execute('get_vercel_status', {'component': 'Builds'})
        incident = status['incidents'][0]['id']
        details = tools.execute('get_incident_details', {'provider': 'vercel', 'incident_id': incident})
        provider = ScriptedProvider([
            call('s', 'get_vercel_status', {'component': 'Builds'}),
            final('Incident ' + incident + ' resolved.'),
            call('d', 'get_incident_details', {'provider': 'vercel', 'incident_id': incident}),
            final('Incident ' + incident + ' resolved. ' + details['url']),
        ])
        result = run_agent('Điều tra incident Builds', provider, tools)
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(any(t['event'] == 'validation_missing_details' for t in result['trace']))

    def test_failed_details_can_report_partial_result(self):
        tools = BonusTools(scenario='format_once')
        provider = ScriptedProvider([
            call('d', 'get_incident_details', {'provider': 'npm', 'incident_id': 'missing'}),
            final('Chưa lấy được chi tiết incident.'),
        ])
        self.assertEqual(run_agent('Kiểm tra', provider, tools)['status'], 'completed')
