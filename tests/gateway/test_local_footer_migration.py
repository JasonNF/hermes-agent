from types import SimpleNamespace

from gateway.config import Platform
from gateway.run_turn_runner import TurnRunner
from gateway.turn_context import TurnContext


def test_completed_stream_and_returned_response_share_one_footer():
    source = SimpleNamespace(platform=Platform.TELEGRAM)
    ctx = TurnContext(source=source)
    ctx.user_config = {'display': {'runtime_footer': {'enabled': True, 'fields': ['model']}}}
    ctx.agent_holder[0] = SimpleNamespace(model='test-model', context_compressor=None)
    runner = TurnRunner(SimpleNamespace(_reasoning_config={}), ctx)
    delivered = []
    consumer = SimpleNamespace(finish=lambda text=None: delivered.append(text))
    result = {'final_response': 'answer', 'completed': True, 'messages': []}
    runner._finish_stream_consumer(result, [], consumer)
    assert delivered == [result['final_response']]
    assert result['final_response'] == 'answer\n\ntest-model'
    assert result['footer_included_in_final_response'] is True
    interrupted = {'final_response': 'interrupted', 'interrupted': True}
    runner._finish_stream_consumer(interrupted, [], consumer)
    assert delivered[-1] is None
    assert 'footer_included_in_final_response' not in interrupted
