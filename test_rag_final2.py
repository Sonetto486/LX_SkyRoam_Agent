import sys
sys.path.insert(0, 'scripts')
from rag_api import answer_question
import asyncio

async def test():
    print('='*60)
    print('测试: 北京有什么好吃的')
    print('='*60)
    result = await answer_question('北京有什么好吃的')
    print('\n回答:')
    print(result.get('answer', '无回答')[:600])
    print('\n来源数量:', len(result.get('sources', [])))

asyncio.run(test())
